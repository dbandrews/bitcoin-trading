import numpy as np

from sklearn.model_selection._split import _BaseKFold, indexable, _num_samples
from sklearn.utils.validation import _deprecate_positional_args

from scipy.ndimage.filters import uniform_filter1d

# Plotting
from matplotlib.colors import ListedColormap
import matplotlib.pyplot as plt

# modified code for group gaps; source
# https://github.com/getgaurav2/scikit-learn/blob/d4a3af5cc9da3a76f0266932644b884c99724c57/sklearn/model_selection/_split.py#L2243
class PurgedGroupTimeSeriesSplit(_BaseKFold):
    """Time Series cross-validator variant with non-overlapping groups.
    Allows for a gap in groups to avoid potentially leaking info from
    train into test if the model has windowed or lag features.
    Provides train/test indices to split time series data samples
    that are observed at fixed time intervals according to a
    third-party provided group.
    In each split, test indices must be higher than before, and thus shuffling
    in cross validator is inappropriate.
    This cross-validation object is a variation of :class:`KFold`.
    In the kth split, it returns first k folds as train set and the
    (k+1)th fold as test set.
    The same group will not appear in two different folds (the number of
    distinct groups has to be at least equal to the number of folds).
    Note that unlike standard cross-validation methods, successive
    training sets are supersets of those that come before them.
    Read more in the :ref:`User Guide <cross_validation>`.
    Parameters
    ----------
    n_splits : int, default=5
        Number of splits. Must be at least 2.
    max_train_group_size : int, default=Inf
        Maximum group size for a single training set.
    group_gap : int, default=None
        Gap between train and test
    max_test_group_size : int, default=Inf
        We discard this number of groups from the end of each train split
    """

    @_deprecate_positional_args
    def __init__(
        self,
        n_splits=5,
        *,
        max_train_group_size=np.inf,
        max_test_group_size=np.inf,
        group_gap=None,
        verbose=False
    ):
        super().__init__(n_splits, shuffle=False, random_state=None)
        self.max_train_group_size = max_train_group_size
        self.group_gap = group_gap
        self.max_test_group_size = max_test_group_size
        self.verbose = verbose

    def split(self, X, y=None, groups=None):
        """Generate indices to split data into training and test set.
        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)
            Training data, where n_samples is the number of samples
            and n_features is the number of features.
        y : array-like of shape (n_samples,)
            Always ignored, exists for compatibility.
        groups : array-like of shape (n_samples,)
            Group labels for the samples used while splitting the dataset into
            train/test set.
        Yields
        ------
        train : ndarray
            The training set indices for that split.
        test : ndarray
            The testing set indices for that split.
        """
        if groups is None:
            raise ValueError("The 'groups' parameter should not be None")
        X, y, groups = indexable(X, y, groups)
        n_samples = _num_samples(X)
        n_splits = self.n_splits
        group_gap = self.group_gap
        max_test_group_size = self.max_test_group_size
        max_train_group_size = self.max_train_group_size
        n_folds = n_splits + 1
        group_dict = {}
        u, ind = np.unique(groups, return_index=True)
        unique_groups = u[np.argsort(ind)]
        n_samples = _num_samples(X)
        n_groups = _num_samples(unique_groups)
        for idx in np.arange(n_samples):
            if groups[idx] in group_dict:
                group_dict[groups[idx]].append(idx)
            else:
                group_dict[groups[idx]] = [idx]
        if n_folds > n_groups:
            raise ValueError(
                (
                    "Cannot have number of folds={0} greater than"
                    " the number of groups={1}"
                ).format(n_folds, n_groups)
            )

        group_test_size = min(n_groups // n_folds, max_test_group_size)
        group_test_starts = range(
            n_groups - n_splits * group_test_size, n_groups, group_test_size
        )
        for group_test_start in group_test_starts:
            train_array = []
            test_array = []

            group_st = max(0, group_test_start - group_gap - max_train_group_size)
            for train_group_idx in unique_groups[
                group_st : (group_test_start - group_gap)
            ]:
                train_array_tmp = group_dict[train_group_idx]

                train_array = np.sort(
                    np.unique(
                        np.concatenate((train_array, train_array_tmp)), axis=None
                    ),
                    axis=None,
                )

            train_end = train_array.size

            for test_group_idx in unique_groups[
                group_test_start : group_test_start + group_test_size
            ]:
                test_array_tmp = group_dict[test_group_idx]
                test_array = np.sort(
                    np.unique(np.concatenate((test_array, test_array_tmp)), axis=None),
                    axis=None,
                )

            test_array = test_array[group_gap:]

            if self.verbose > 0:
                pass

            yield [int(i) for i in train_array], [int(i) for i in test_array]


# Adopted from: https://scikit-learn.org/stable/auto_examples/model_selection/plot_cv_indices.html
def plot_cv_indices(
    cv, X, y, group, ax, n_splits, lw=10, group_name="day", moving_average=None
):
    """Plots a visual of the specified CV splitter with sample time series data

    Parameters
    ----------
    cv : sklearn CV splitter
        A sklearn CV splitter for splitting the data
    X : array
        example training data X
    y : array
        example training data y
    group : array
        example training data groups, same length as X
    ax : Axes
        matplotlib axes to plot onto
    n_splits : int
        number of cv splits to use
    lw : int, optional
        line width of markers, by default 10
    group_name : str, optional
        label for group series, by default "day"
    moving_average : int, optional
        if an integer is supplied, a moving average of that length is added to the example data, by default None means not to plot

    Returns
    -------
    ax
        matplotlib Axes object
    """

    cmap_cv = plt.cm.coolwarm

    jet = plt.cm.get_cmap("jet", 256)
    seq = np.linspace(0, 1, 256)
    _ = np.random.shuffle(seq)  # inplace
    cmap_data = ListedColormap(jet(seq))

    # Build some noise to simulate random walk
    # Using Brownian motion:
    T = len(X)
    σ = 0.05

    prices = np.arange(T)
    σ = np.repeat(σ, T)
    Z = np.random.randn(T)
    theta = np.exp(-0.5 * σ ** 2 + σ * Z)

    noise = 1 * theta.cumprod() - 1

    # Generate the training/testing visualizations for each CV split
    for ii, (tr, tt) in enumerate(cv.split(X=X, y=y, groups=group)):
        # Fill in indices with the training/test groups
        indices = np.array([np.nan] * len(X))
        indices[tt] = 1
        indices[tr] = 0

        # Visualize the results
        ax.plot(
            range(len(indices)),
            [ii + 0.5] * len(indices) + noise,
            c="darkgrey",
            # marker="_",
            lw=2,
            # cmap=cmap_cv,
        )

        ax.scatter(
            range(len(indices)),
            [ii + 0.5] * len(indices) + noise,
            c=indices,
            # marker="_",
            s=100,
            lw=1,
            cmap=cmap_cv,
            vmin=-0.2,
            vmax=1.2,
        )

        # Add moving average for more demo's
        if moving_average is not None:

            # Calculate a moving average by convolution over a window size with 1's
            moving_average_signal = uniform_filter1d(
                [ii + 0.5] * len(indices) + noise, size=moving_average
            )

            ax.plot(
                range(len(indices)),
                moving_average_signal,
                c="red",
                # marker="_",
                lw=1,
                # cmap=cmap_cv,
            )

    # Plot the data classes and groups at the end
    ax.scatter(
        range(len(X)), [ii + 1.5] * len(X), c=y, marker="_", lw=lw, cmap=plt.cm.Set3
    )

    ax.scatter(
        range(len(X)), [ii + 2.5] * len(X), c=group, marker="_", lw=lw, cmap=cmap_data
    )

    # Formatting
    yticklabels = list(range(n_splits)) + ["target", group_name]
    ax.set(
        yticks=np.arange(n_splits + 2) + 0.5,
        yticklabels=yticklabels,
        xlabel="Sample index",
        ylabel="CV iteration",
        ylim=[n_splits + 2.2, -0.2],
        xlim=[0, len(y)],
    )

    ax.set_title("{}".format(type(cv).__name__), fontsize=15)
    return ax


def simulate_np(S0=1, σ=0.1, T=1000):
    """
    Calculates a simulated Brownian motion for stock price.

    Parameters
    ----------
    S0: float
        Initial stock price
    σ: float
        Volatility of the stock
    T: int
        Number of time steps to simulate over

    Returns
    -------
    list[float] :
        Simulated stock price over T time steps

    Examples
    --------
    >>>simulate(10,0.1,10)
    array([10.90355263, 10.07348102, 12.19974705, 10.0306349 ,  9.32654282,
        7.82230874,  7.58329327,  7.19078946,  6.87241673,  5.78931361])

    """
    prices = np.arange(T)
    σ = np.repeat(σ, T)
    Z = np.random.randn(T)
    theta = np.exp(-0.5 * σ ** 2 + σ * Z)

    prices = S0 * theta.cumprod()

    return prices