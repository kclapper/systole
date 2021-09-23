# Author: Nicolas Legrand <nicolas.legrand@cfin.au.dk>

import itertools
from typing import List, Optional, Tuple, Union

import numpy as np
import seaborn as sns
from bokeh.plotting.figure import Figure
from matplotlib.axes import Axes

from systole.detection import ecg_peaks, ppg_peaks
from systole.plots.utils import get_plotting_function
from systole.utils import heart_rate, to_epochs


def plot_evoked(
    epochs: Optional[np.ndarray] = None,
    signal: Optional[np.ndarray] = None,
    triggers: Optional[np.ndarray] = None,
    triggers_idx: Optional[np.ndarray] = None,
    rr: Optional[np.ndarray] = None,
    input_type: str = "peaks",
    reject: Optional[np.ndarray] = None,
    modality: str = "ppg",
    tmin: float = -1.0,
    tmax: float = 10.0,
    sfreq: int = 1000,
    apply_baseline: Optional[Union[float, Tuple[float, float]]] = 0.0,
    decim: Optional[int] = None,
    labels: Optional[Union[str, List[str]]] = None,
    unit: str = "bpm",
    kind: str = "cubic",
    ci: Union[int, str] = "sd",
    ax: Optional[Axes] = None,
    figsize: Optional[Tuple[float, float]] = None,
    backend: str = "matplotlib",
    palette: Optional[List[str]] = None,
    **kwargs,
) -> Union[Figure, Axes]:
    """Plot events occurence across recording.

    Parameters
    ----------
    epochs : np.array
        A 2d (trial * time) numpy array containing the time series of the epoched
        signal.
    signal : np.array
        A 1d numpy array containing the physiological signal (can be PPG or
        ECG). The modality of the signal is parametrized using the `modality`
        parameter.
    triggers : np.ndarray | list
        The boolean indices of the events, shape=(times*sfreq, 1).
    triggers_idx : np.ndarray or list
        Trigger indexes. Each value encode the sample where an event occured (see
        also `sfreq`). Different conditions should be provided separately as list of
        arrays (can have different lenght).
    rr : np.array | list
        Boolean vector of peaks detection or peaks indexs. See `input_type`.
    input_type : str
        The type of input vector. Can be `"peaks"`, `"peaks_idx"`, `"rr_ms"`,
        or `"rr_s"`. Default to `"peaks"`.
    reject : np.ndarray | None
        Segments of the signal that should be rejected.
    modality : str
        The recording modality (can be `"ppg"` or `"ecg"`). Only required when using
        `signal`. The modality will determine the peaks detection method.
    tmin, tmax : float
        Start and end time of the epochs in seconds, relative to the
        time-locked event. Defaults to -1.0 and 10.0, respectively.
    sfreq : int
        The sampling frequency of the input signal and triggers. Default set to `1000`.
    apply_baseline : float | tuple | None
        If int or tuple, use the point or interval to apply a baseline
        (method: mean). If `None`, no baseline is applied. Default is set to `0`.
    decim : int | None
        Factor by which to subsample the data. Selects every Nth sample (where N is the
        value passed to decim). Default set to `None` (no decim).
    labels : str or list
        The condition labels.
    unit : str
        The heart rate unit. Can be `'rr'` (R-R intervals, in ms) or `'bpm'` (beats
        per minutes). Default is `'bpm'`.
    kind : str
        This argument will be passed too py:func:`systole.utils.heart_rate` and control
        the type of interpolation between instantaneous heart rate estimates.
        This is then the method used by `scipy.interpolate.interp1d`). Can be `'cubic'`
        (defalut), `'linear'`, `'previous'` or `'next'`.
    ci : int | str
        The confidence interval around the mean estimate. If `backend="matplotlib"`,
        this value will be passed to py:func:`seaborn.lineplot`. If `backend="bokeh"`,
        only `"sd"` (standard deviation) is currently supported. Default set to `"sd"`.
    ax : :class:`matplotlib.axes.Axes` | None
        Where to draw the plot. Default is *None* (create a new figure).
    figsize : tuple, int or None
        Figure size. Default is set to `(13, 5)` if `backend=="matplotlib"` and
        `(400, 400)` if `backend=="bokeh"`.
    backend: str
        Select plotting backend (`"matplotlib"`, `"bokeh"`). Default sets to
        `"matplotlib"`.
    palette : list | None
        Color palette. Default sets to Seaborn `"deep"`.
    kwargs: key, value mappings
        Other keyword arguments are passed down to py:`func:seaborn.lineplot()`.

    Returns
    -------
    plot : :class:`matplotlib.axes.Axes` or :class:`bokeh.plotting.figure.Figure`
        The matplotlib axes, or the boken figure containing the plot.

    """
    # Define color palette
    if palette is None:
        this_palette = itertools.cycle(sns.color_palette("deep", as_cmap=True))
    elif isinstance(palette, list):
        this_palette = itertools.cycle(palette)
    else:
        raise ValueError("Invalid palette provided.")

    # Define figure size
    if figsize is None:
        if backend == "matplotlib":
            figsize = (13, 5)
        elif backend == "bokeh":
            figsize = (400, 400)

    # Extract instantaneous heart rate
    if isinstance(signal, np.ndarray):
        if modality == "ppg":
            _, peaks = ppg_peaks(signal, sfreq=sfreq)
        elif modality == "ecg":
            _, peaks = ecg_peaks(signal, sfreq=sfreq)
        rr, _ = heart_rate(peaks, kind=kind, unit=unit, input_type="peaks")

    if isinstance(rr, np.ndarray):
        rr, _ = heart_rate(rr, kind=kind, unit=unit, input_type=input_type, sfreq=sfreq)

    # Epoching
    if epochs is None:
        epochs, _ = to_epochs(
            signal=rr,
            triggers=triggers,
            triggers_idx=triggers_idx,
            reject=reject,
            sfreq=sfreq,
            apply_baseline=apply_baseline,
            tmin=tmin,
            tmax=tmax,
        )
        if isinstance(epochs, np.ndarray):
            epochs = [epochs]

    # Define labels
    if labels is None:
        labels = []
        for i in range(len(epochs)):
            labels.append(f"Condition {i+1}")
    elif isinstance(labels, str):
        labels = [labels]

    # Define time vector according to times range and sampling frequency
    time = np.arange(
        round(tmin * sfreq) / sfreq, round(tmax * sfreq) / sfreq, 1 / sfreq
    )

    if decim is not None:
        for i in range(len(epochs)):
            epochs[i] = epochs[i][:, ::decim]
        time = time[::decim]

    plot_evoked_args = {
        "epochs": epochs,
        "time": time,
        "palette": this_palette,
        "ax": ax,
        "figsize": figsize,
        "labels": labels,
        "unit": unit,
        "ci": ci,
    }

    plotting_function = get_plotting_function("plot_evoked", "plot_evoked", backend)
    plot = plotting_function(**plot_evoked_args)

    return plot
