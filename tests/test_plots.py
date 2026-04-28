import pytest
from conftest import make_plot

MPL_KWARGS = dict(tolerance=2, savefig_kwarg={"dpi": 100}, style="default")


# --- Fields ---


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_animated_1d():
    """X-component of magnetic field, implicitly averaged across z."""
    return make_plot("pfd hx_fc -v y".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_static_1d():
    """X-component of magnetic field at the last time step, implicitly averaged across z. Note video is disabled via `time=`."""
    return make_plot("pfd hx_fc -i t=-1 -v y time=".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_animated_2d():
    """2D view of x-component of magnetic field."""
    return make_plot("pfd hx_fc -v y z".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_static_2d():
    """2D view of x-component of magnetic field at the last time step."""
    return make_plot("pfd hx_fc -i t=-1 -v y z time=".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_animated_2d_derived():
    """2D view of magnetic field square-amplitude. Since each component of H is centered differently, and `--derive` doesn't currently support recentering, use the builtin derived field `h2_cc`."""
    return make_plot("pfd h2_cc -v y z".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_animated_2d_idx():
    """2D slice of x-component of magnetic field at the x=1 index."""
    return make_plot("pfd hx_fc -i x=1 -v y z".split(), data_dir="test-3d")


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_animated_2d_pos():
    """2D slice of x-component of magnetic field nearest to y=0.06."""
    return make_plot("pfd hx_fc --pos y=0.06 -v x z".split(), data_dir="test-3d")


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_animated_1d_downsample():
    """Downsample (i.e., coarsen) by a factor of 2."""
    return make_plot("pfd hx_fc --downsample y=2 -v y".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_animated_1d_bin():
    """Downsample via binning, specifying the final dimension size rather than the downsample factor."""
    return make_plot("pfd hx_fc --bin y=8 -v y".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_animated_1d_rolling():
    """Smooth data via a rolling average."""
    return make_plot("pfd hx_fc --roll y=3 -v y".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_static_2d_spectogram():
    """Spectrogram of wavenumber vs. time."""
    return make_plot("pfd ey_ec -f y --mag --pow 2 --pos k_y=0: -v t k_y time= --nan0 --scale log".split())


# --- Turbulence power spectrum ---


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_spectrum_1d():
    """1D power spectrum of the x-component of the magnetic field. Note `--pos` and `-i` to remove negative and 0-mode, respectively. The `--mul 2` recovers the (symmetric) power of negative modes."""
    return make_plot("pfd hx_fc -f y z --mag --pow 2 -v k_y --pos k_y=0: -i k_y=1: --mul 2 --scale log k_y=log".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_spectrum_3d():
    """Total power spectrum of the magnetic field. The builtin `hhat2` is the sum of the squares of the Fourier-transformed copmonents of the magnetic field. The combination of `--scatter` and `--transform-spherical` avoids interpolating onto a grid when doing the coordinate transformation. Note `--pos` removes the 0-mode. This is the current intended use case for `--fit`, which fits a power law index, but also necessitates `--compute` due to a bug."""
    return make_plot("pfd hhat2 --scatter --transform-spherical k_y k_z k_x --pos k_s=1e-8: -v k_s hhat2 --scale hhat2=log --compute --fit 25:45".split(), data_dir="test-3d")


# --- Particles ---


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_animated_scatter_electron_positions():
    """A real-space scatter plot of electron positions, with cell edges shown via `--grid`. Grid line positions aren't coordinate-informed, so the spacing is manually specified."""
    return make_plot("prt --species e -v y z --grid y=0.0625 z=0.0625".split(), data_dir="test-3d")


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_animated_scatter_ion_phase():
    """A phase-space scatter plot of ions. Color is used to show pz, but requires `--compute` due to a bug."""
    return make_plot("prt --species i -v y py color=pz --compute".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_animated_2d_binned_phase():
    """A clearer way to see phase space distributions for many particles. Since y is a dimension with coordinates, those coordinates are automatically used as bin edges. The combination of `--nan0` and `--scale log` makes faint phase-space structures very easy to see."""
    return make_plot("prt --species i --bin y py=16 -v y py --nan0 --scale log".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_static_scatter():
    """Static scatter plot of electron positions at the last time step."""
    return make_plot("prt --species e -i t=-1 -v y z time= --grid y=0.0625 z=0.0625".split(), data_dir="test-3d")


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_animated_scatter_with_variable():
    """Scatter plot with explicit variable: py on y-axis, y on x-axis."""
    return make_plot("prt py --species i -v y".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_animated_scatter_mul():
    """Scatter plot with --mul applied to the active variable."""
    return make_plot("prt py --species i --mul 2 -v y".split())


# --- Particles (ADIOS2 .bp) ---
# Each test points at the same baseline PNG as its H5 counterpart. Test data
# was generated from the same PSC runs for both formats, so the plots should
# match pixel-for-pixel within the existing tolerance.


@pytest.mark.mpl_image_compare(filename="test_animated_scatter_ion_phase.png", **MPL_KWARGS)
def test_animated_scatter_ion_phase_bp():
    """BP twin of test_animated_scatter_ion_phase."""
    return make_plot("prt.i -v y py color=pz --compute".split())


@pytest.mark.mpl_image_compare(filename="test_animated_2d_binned_phase.png", **MPL_KWARGS)
def test_animated_2d_binned_phase_bp():
    """BP twin of test_animated_2d_binned_phase."""
    return make_plot("prt.i --bin y py=16 -v y py --nan0 --scale log".split())


@pytest.mark.mpl_image_compare(filename="test_static_scatter.png", **MPL_KWARGS)
def test_static_scatter_bp():
    """BP twin of test_static_scatter."""
    return make_plot("prt.e -i t=-1 -v y z time= --grid y=0.0625 z=0.0625".split(), data_dir="test-3d")


# --- Particle moments ---


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_static_1d_rho_i():
    """A typical plot of initial ion charge density, implicitly averaged across z."""
    return make_plot("pfd_moments rho_i -v y time=".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_static_1d_rho_derive():
    """Use --derive to get the total charge density, like so. Note that some initial field must be set (rho_i), but the result of --derive is what ends up being plotted."""
    return make_plot("pfd_moments rho_i --derive rho=rho_i+rho_e -v y time=".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_static_1d_rho():
    """Total charge density is also (currently) a predefined deriveable variable."""
    return make_plot("pfd_moments rho -v y time=".split())


# --- Gauss error ---


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_gauss_spatial():
    """Maximum absolute error in Gauss' law. Note `mag` (magnitude, or absolute value) before `--reduce`. As usual, `--nan0` and `--scale log` play well together."""
    return make_plot("gauss error --mag --reduce x,z=max -v y --nan0 --scale log".split(), data_dir="test-3d")


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_gauss_temporal():
    """Maximum absolte error in Gauss' law as a function of time. Note `time=` in `-v` to disable the default behavior of `time=t`."""
    return make_plot("gauss error --mag --reduce x,y,z=max -v t time= --nan0 --scale log".split(), data_dir="test-3d")


# --- Misc ---


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_vline():
    """`--vline` supports a labeled and unlabeled version."""
    return make_plot("prt -v y z --vline 0.15=label 0.03".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_scale_symlog():
    """Symlog scale with specific linear threshold."""
    return make_plot("pfd hx_fc -v y z --scale symlog#.01".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_polar_grid():
    """Polar plot."""
    return make_plot("pfd hx_fc --transform-polar y z -v r_p theta".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_static_polar():
    """Static polar plot at the last time step."""
    return make_plot("pfd hx_fc -i t=-1 --transform-polar y z -v r_p theta time=".split())


# --- Display/unit overrides ---


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_display_override():
    """`--display NAME=VALUE` overrides the LaTeX rendering of the named variable."""
    return make_plot("pfd hx_fc -v y --display hx_fc=\\text{test}".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_display_override_dim():
    """`--display DIM=VALUE` overrides the LaTeX rendering of a dimension's axis label."""
    return make_plot("pfd hx_fc -v y --display y=\\chi".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_unit_override():
    """`--unit NAME=VALUE` appends a unit bracket to the axis label."""
    return make_plot("pfd hx_fc -v y --unit hx_fc=\\text{test}".split())


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_unit_override_dim():
    """`--unit DIM=VALUE` overrides the unit shown in a dimension's axis label."""
    return make_plot("pfd hx_fc -v y --unit y=\\text{test}".split())


def test_field_units_lookup_covers_test_data():
    """All raw vars present in the test-2d datasets resolve via the registry (no fallback)."""
    from lib.var_info_registry import _REGISTRY

    expected_pfd = {"hx_fc", "hy_fc", "hz_fc", "ex_ec", "ey_ec", "ez_ec", "jx_ec", "jy_ec", "jz_ec"}
    expected_moments = {
        *(f"{m}_{s}" for m in ("rho", "jx", "jy", "jz", "px", "py", "pz", "txx", "tyy", "tzz", "txy", "tyz", "tzx") for s in ("e", "i")),
    }
    expected_gauss = {"dive", "rho"}

    for v in expected_pfd:
        assert ("pfd", v) in _REGISTRY, v
    for v in expected_moments:
        assert ("pfd_moments", v) in _REGISTRY, v
    for v in expected_gauss:
        assert ("gauss", v) in _REGISTRY, v
