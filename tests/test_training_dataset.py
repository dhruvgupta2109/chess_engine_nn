import torch

from chess_engine_nn.encoding import FEATURE_COUNT
from chess_engine_nn.training.dataset import JsonlPositionDataset


def test_indexed_dataset_reads_each_split(training_dataset) -> None:
    train = JsonlPositionDataset(training_dataset, "train", target_cap_cp=1_000)
    validation = JsonlPositionDataset(training_dataset, "validation", target_cap_cp=1_000)
    assert len(train) == 18
    assert len(validation) == 6
    features, target = train[0]
    assert features.shape == (FEATURE_COUNT,)
    assert features.dtype == torch.float32
    assert target.dtype == torch.float32


def test_dataset_clips_targets(training_dataset) -> None:
    dataset = JsonlPositionDataset(training_dataset, "validation", target_cap_cp=50)
    targets = [float(dataset[index][1]) for index in range(len(dataset))]
    assert max(targets) == 1.0
    assert min(targets) == -1.0
