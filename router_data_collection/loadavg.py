from influxdb_client import Point

from router_data_collection.metric import ValueMetric


class Loadavg:
  WATCH_CAT_FILE = '/proc/loadavg'
  MEASUREMENT = 'proc_loadavg'
  SCALE_FACTOR = 100

  def __init__(self) -> None:
    self.fields = [
        ValueMetric(self.MEASUREMENT,
                    tags={'scale_factor': str(self.SCALE_FACTOR)},
                    field='loadavg_1m'),
        ValueMetric(self.MEASUREMENT,
                    tags={'scale_factor': str(self.SCALE_FACTOR)},
                    field='loadavg_5m'),
        ValueMetric(self.MEASUREMENT,
                    tags={'scale_factor': str(self.SCALE_FACTOR)},
                    field='loadavg_15m'),
        ValueMetric(self.MEASUREMENT, tags={}, field='running_processes'),
        ValueMetric(self.MEASUREMENT, tags={}, field='total_processes'),
        ValueMetric(self.MEASUREMENT, tags={}, field='last_process_id'),
    ]
    self.initial_updated = False

  def generate_points(self, output: dict[str, list[str]], time_ns: int) -> list[Point]:
    lines = output[self.WATCH_CAT_FILE]
    assert len(lines) == 1
    values = lines[0].split()

    if not self.initial_updated:
      self.fields[0].initial_update(self._scale_float(values[0]))
      self.fields[1].initial_update(self._scale_float(values[1]))
      self.fields[2].initial_update(self._scale_float(values[2]))
      self.fields[3].initial_update(int(values[3].split('/')[0]))
      self.fields[4].initial_update(int(values[3].split('/')[1]))
      self.fields[5].initial_update(int(values[4]))
      self.initial_updated = True
      return []

    points = [
        self.fields[0].update(self._scale_float(values[0]), time_ns),
        self.fields[1].update(self._scale_float(values[1]), time_ns),
        self.fields[2].update(self._scale_float(values[2]), time_ns),
        self.fields[3].update(int(values[3].split('/')[0]), time_ns),
        self.fields[4].update(int(values[3].split('/')[1]), time_ns),
        self.fields[5].update(int(values[4]), time_ns),
    ]
    return [p for p in points if p is not None]

  def _scale_float(self, value: float | str) -> int:
    return round(float(value) * self.SCALE_FACTOR)
