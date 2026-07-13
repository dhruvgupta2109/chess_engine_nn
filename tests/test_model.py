import torch

from chess_engine_nn.encoding import FEATURE_COUNT
from chess_engine_nn.model import ClippedReLU, ModelConfig, NnueValueNetwork


def test_model_shape_and_bounds() -> None:
    config = ModelConfig(accumulator_dim=16, hidden_dim=8, target_cap_cp=1_000)
    model = NnueValueNetwork(config)
    output = model(torch.zeros((3, FEATURE_COUNT)))
    assert output.shape == (3,)
    assert torch.all(output >= -1) and torch.all(output <= 1)
    scores = model.to_centipawns(torch.tensor([-2.0, 0.25, 2.0]))
    assert scores.tolist() == [-1_000, 250, 1_000]


def test_clipped_relu_is_bounded() -> None:
    values = ClippedReLU()(torch.tensor([-1.0, 0.5, 2.0]))
    assert values.tolist() == [0.0, 0.5, 1.0]


def test_invalid_model_metadata_is_rejected() -> None:
    config = ModelConfig(input_dim=1)
    try:
        config.validate()
    except ValueError as error:
        assert "input_dim" in str(error)
    else:
        raise AssertionError("invalid model config was accepted")
