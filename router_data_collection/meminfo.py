from influxdb_client import Point

from router_data_collection.metric import ValueMetric


class Meminfo:
  WATCH_CAT_FILE = '/proc/meminfo'
  MEASUREMENT = 'proc_meminfo'

  def __init__(self) -> None:
    self.fields: dict[str, ValueMetric] = dict()

  def generate_points(self, output: dict[str, list[str]], time_ns: int) -> list[Point]:
    lines = output[self.WATCH_CAT_FILE]
    points: list[Point | None] = []

    for line in lines:
      field, value = self._parse_line(line)
      if field not in self.fields:
        self.fields[field] = self._new_metric(field, value)
        continue

      metric = self.fields[field]
      points.append(metric.update(value, time_ns))

    return [p for p in points if p is not None]

  def _parse_line(self, line: str) -> tuple[str, int]:
    field, value, unit = line.split()
    assert unit == 'kB'
    return (field[:-1], int(value))

  def _new_metric(self, field: str, value: int) -> ValueMetric:
    metric = ValueMetric(measurement=self.MEASUREMENT, tags={'unit': 'kiB'}, field=field)
    metric.initial_update(value)
    return metric


# Interpreting /proc/meminfo and free output
# https://access.redhat.com/solutions/406773
