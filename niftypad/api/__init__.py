"""Clean API"""
import logging
from pathlib import Path

from . import readers

log = logging.getLogger(__name__)


def kinetic_model(src, dst=None, params=None, model='srtmb_basis', w=None, r1=0.905, k2p=0.000250,
                  beta_lim=None, n_beta=40, linear_phase_start=500, linear_phase_end=None,
                  km_outputs=None, thr=0.1, fig=False):
    """
    Args:
      src (Path or str): input patient directory or filename
      dst (Path or str): output directory (default: `src` directory)
      params (Path or str): config (relative to `src` directory)
      model (str): srtmb_basis, srtmb_k2p_basis, srtmb_asl_basis, logan_ref, logan_ref_k2p,
        mrtm, mrtm_k2p
    """
    import nibabel as nib
    import numpy as np

    from niftypad import basis
    from niftypad.image_process.parametric_image import image_to_parametric
    from niftypad.models import get_model_inputs
    from niftypad.tac import Ref

    src_path = Path(src)
    if src_path.is_dir():
        fpath = next(src_path.glob('*.nii'))
    else:
        fpath = src_path
        src_path = fpath.parent
    log.debug("file:%s", fpath)

    if dst is None:
        dst_path = src_path
    else:
        dst_path = Path(dst)
        assert dst_path.is_dir()

    meta = readers.find_meta(src_path, filter(None, [params, fpath.stem]))
    dt = np.asarray(meta['dt'])
    ref = np.asarray(meta['ref'])
    ref = Ref(ref, dt)
    ref.interp_1cubic()

    log.debug("looking for first `*.nii` file in %s", src_path)
    img = nib.load(fpath)
    # pet_image = img.get_fdata(dtype=np.float32)
    pet_image = np.asanyarray(img.dataobj)

    # basis functions
    if beta_lim is None:
        beta_lim = [0.01 / 60, 0.3 / 60]
    b = basis.make_basis(ref.inputf1cubic, dt, beta_lim=beta_lim, n_beta=n_beta, w=w, k2p=k2p)

    if km_outputs is None:
        km_outputs = ['R1', 'k2', 'BP']

    user_inputs = {
        'dt': dt, 'inputf1': ref.inputf1cubic, 'w': w, 'r1': r1, 'k2p': k2p, 'beta_lim': beta_lim,
        'n_beta': n_beta, 'b': b, 'linear_phase_start': linear_phase_start,
        'linear_phase_end': linear_phase_end, 'fig': fig}
    model_inputs = get_model_inputs(user_inputs, model)
    # log.debug("model_inputs:%s", model_inputs)

    parametric_images_dict, pet_image_fit = image_to_parametric(pet_image, dt, model, model_inputs,
                                                                km_outputs, thr=thr)
    for kp in parametric_images_dict:
        nib.save(nib.Nifti1Image(parametric_images_dict[kp], img.affine),
                 f"{dst_path / fpath.stem}_{model}_{kp}_{fpath.suffix}")
    nib.save(nib.Nifti1Image(pet_image_fit, img.affine),
             f"{dst_path / fpath.stem}_{model}_fit_{fpath.suffix}")
