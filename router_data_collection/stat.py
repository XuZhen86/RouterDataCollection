from influxdb_client import Point

from router_data_collection.metric import ValueMetric


class Stat:
  WATCH_CAT_FILE = '/proc/stat'
  MEASUREMENT = 'proc_stat'
  # https://man7.org/linux/man-pages/man5/proc.5.html
  CPU_FIELDS = [
      'user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq', 'steal', 'guest', 'guest_nice'
  ]

  def __init__(self) -> None:
    self.cpu_metrics: dict[str, list[ValueMetric]] = dict()

  def generate_points(self, output: dict[str, list[str]], time_ns: int) -> list[Point]:
    lines = output[self.WATCH_CAT_FILE]
    points: list[Point | None] = []

    for line in lines:
      segments = line.split()

      if segments[0].startswith('cpu'):
        points.extend(self._process_cpu(segments, time_ns))

    return [p for p in points if p is not None]

  def _process_cpu(self, segments: list[str], time_ns: int) -> list[Point | None]:
    cpu_id = segments[0]
    values = [int(value) for value in segments[1:]]
    assert len(values) == len(self.CPU_FIELDS)

    if cpu_id not in self.cpu_metrics:
      metrics = [
          self._new_cpu_metric(field, value, cpu_id)
          for field, value in zip(self.CPU_FIELDS, values)
      ]
      self.cpu_metrics[cpu_id] = metrics
      return []

    metrics = self.cpu_metrics[cpu_id]
    points: list[Point | None] = []

    for metric, value in zip(metrics, values):
      points.append(metric.update(value, time_ns))

    return points

  def _new_cpu_metric(self, field: str, value: int, cpu_id: str) -> ValueMetric:
    metric = ValueMetric(
        measurement=self.MEASUREMENT,
        tags={
            'type': 'cpu',
            'id': cpu_id,
            'unit': 'user_hz'
        },
        field=field,
    )
    metric.initial_update(value)
    return metric
