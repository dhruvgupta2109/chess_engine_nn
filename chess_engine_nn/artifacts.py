"""Runtime-safe inference artifact constants and checksum helpers."""

import hashlib

import torch

INFERENCE_ARTIFACT_VERSION = 1


def state_dict_sha256(state: dict[str, torch.Tensor]) -> str:
    """Hash tensor names, types, shapes, and bytes deterministically."""
    digest = hashlib.sha256()
    for name in sorted(state):
        tensor = state[name].detach().cpu().contiguous()
        digest.update(name.encode())
        digest.update(str(tensor.dtype).encode())
        digest.update(str(tuple(tensor.shape)).encode())
        digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()
