from dataclasses import dataclass

from absl import flags
from influxdb_client import Point

_INACTIVE_METRIC_TIMEOUT_S = flags.DEFINE_float(
    name='inactive_metrics_timeout_s',
    default=30,
    help='Stop producing data points for a metric if the it has not changed for the past x seconds.',
)


@dataclass
class PositiveRateMetric:
  measurement: str
  tags: dict[str, str]
  scale_factor: int
  field: str

  _value: int = 0
  _last_seen_ns: int = 0  # Always updated upon setting a value.
  _last_updated_ns: int = 0  # Only updated upon setting a different value.

  def initial_update(self, value: int, time_ns: int) -> None:
    self._value = value
    self._last_seen_ns = time_ns
    # self._last_updated_ns = time_ns

  def update(self, value: int, time_ns: int) -> Point | None:
    elapsed_ns = time_ns - self._last_seen_ns
    self._last_seen_ns = time_ns

    # Stop producing points if the value has not changed for a while.
    if self._value == value and time_ns - self._last_updated_ns > float(
        _INACTIVE_METRIC_TIMEOUT_S.value) * 10**9:
      return

    increment = self._calculate_increment(value)
    rate = self._calculate_rate(increment, elapsed_ns)

    point = Point(self.measurement)
    for tag, tag_value in self.tags.items():
      point.tag(tag, tag_value)
    point.tag('scale_factor', self.scale_factor)
    point.field(self.field, rate)
    point.time(time_ns)  # type: ignore

    if self._value != value:
      self._value = value
      self._last_updated_ns = time_ns

    return point

  def _calculate_increment(self, value: int) -> int:
    if self._value <= value:
      return value - self._value

    # It could be either uint32 or uint64 overflow. Making a guess by using the smaller difference.
    uint32_difference = 2**32 - self._value
    uint64_difference = 2**64 - self._value
    return min(uint32_difference, uint64_difference) + value

  def _calculate_rate(self, increment: int, elapsed_ns: int) -> int:
    return round(increment * 10**9 * self.scale_factor / elapsed_ns)


@dataclass
class ValueMetric:
  measurement: str
  tags: dict[str, str]
  field: str

  _value: int = 0
  _last_updated_ns: int = 0  # Only updated upon setting a different value.

  def initial_update(self, value: int) -> None:
    self._value = value

  def update(self, value: int, time_ns: int) -> Point | None:
    # Stop producing points if the value has not changed for a while.
    if self._value == value and time_ns - self._last_updated_ns > float(
        _INACTIVE_METRIC_TIMEOUT_S.value) * 10**9:
      return

    point = Point(self.measurement)
    for tag, tag_value in self.tags.items():
      point.tag(tag, tag_value)
    point.field(self.field, value)
    point.time(time_ns)  # type: ignore

    if self._value != value:
      self._value = value
      self._last_updated_ns = time_ns

    return point


@dataclass
class StateMetric:
  measurement: str
  tags: dict[str, str]
