from enum import StrEnum, unique

from influxdb_client import Point

from router_data_collection.metric import PositiveRateMetric


@unique
class Fields(StrEnum):
  BYTES = 'bytes'
  PACKETS = 'packets'
  ERRORS = 'errs'
  DROPPED_PACKETS = 'drop'
  FIFO_BUFFER_ERRORS = 'fifo'
  FRAMING_ERRORS = 'frame'
  COMPRESSED_PACKETS = 'compressed'
  MULTICAST_FRAMES = 'multicast'
  COLLISIONS = 'colls'
  CARRIER_LOSSES = 'carrier'


@unique
class Units(StrEnum):
  BYTES_PER_SECOND = 'bytes/s'
  PACKETS_PER_SECOND = 'packets/s'
  ERRORS_PER_SECOND = 'errors/s'
  FRAMES_PER_SECOND = 'frames/s'
  COLLISIONS_PER_SECOND = 'collisions/s'
  LOSSES_PER_SECOND = 'losses/s'


@unique
class Directions(StrEnum):
  RECEIVE = 'receive'
  TRANSMIT = 'transmit'


class NetDev:
  WATCH_CAT_FILE = '/proc/net/dev'
  MEASUREMENT = 'proc_net_dev'
  SCALE_FACTOR = 10**6

  # https://web.archive.org/web/20180522173537/http://www.linuxdevcenter.com/pub/a/linux/2000/11/16/LinuxAdmin.html
  RX_FIELDS = [
      Fields.BYTES, Fields.PACKETS, Fields.ERRORS, Fields.DROPPED_PACKETS,
      Fields.FIFO_BUFFER_ERRORS, Fields.FRAMING_ERRORS, Fields.COMPRESSED_PACKETS,
      Fields.MULTICAST_FRAMES
  ]
  RX_UNITS = [
      Units.BYTES_PER_SECOND, Units.PACKETS_PER_SECOND, Units.ERRORS_PER_SECOND,
      Units.PACKETS_PER_SECOND, Units.ERRORS_PER_SECOND, Units.ERRORS_PER_SECOND,
      Units.PACKETS_PER_SECOND, Units.FRAMES_PER_SECOND
  ]
  TX_FIELDS = [
      Fields.BYTES, Fields.PACKETS, Fields.ERRORS, Fields.DROPPED_PACKETS,
      Fields.FIFO_BUFFER_ERRORS, Fields.COLLISIONS, Fields.CARRIER_LOSSES, Fields.COMPRESSED_PACKETS
  ]
  TX_UNITS = [
      Units.BYTES_PER_SECOND, Units.PACKETS_PER_SECOND, Units.ERRORS_PER_SECOND,
      Units.PACKETS_PER_SECOND, Units.ERRORS_PER_SECOND, Units.COLLISIONS_PER_SECOND,
      Units.LOSSES_PER_SECOND, Units.PACKETS_PER_SECOND
  ]

  def __init__(self) -> None:
    self.interfaces: dict[str, list[PositiveRateMetric]] = dict()

  def generate_points(self, output: dict[str, list[str]], time_ns: int) -> list[Point]:
    lines = output[self.WATCH_CAT_FILE]
    points: list[Point | None] = []

    for interface, counts in self._parse_lines(lines).items():
      if interface not in self.interfaces:
        self.interfaces[interface] = self._new_metrics(interface, counts, time_ns)
        continue

      metrics = self.interfaces[interface]

      for i, count in enumerate(counts):
        points.append(metrics[i].update(count, time_ns))

    return [p for p in points if p is not None]

  def _parse_lines(self, lines: list[str]) -> dict[str, list[int]]:
    interfaces: dict[str, list[int]] = dict()
    for line in lines[2:]:
      values = line.split()
      interface = values[0][:-1]
      counts = [int(value) for value in values[1:]]
      interfaces[interface] = counts
    return interfaces

  def _new_metrics(self, interface: str, counts: list[int],
                   time_ns: int) -> list[PositiveRateMetric]:
    rx_metrics: list[PositiveRateMetric] = []
    for field, unit, count in zip(self.RX_FIELDS, self.RX_UNITS, counts[:len(self.RX_FIELDS)]):
      metric = PositiveRateMetric(
          measurement=self.MEASUREMENT,
          tags={
              'interface': interface,
              'direction': Directions.RECEIVE,
              'unit': unit,
          },
          scale_factor=self.SCALE_FACTOR,
          field=field,
      )
      metric.initial_update(count, time_ns)
      rx_metrics.append(metric)

    tx_metrics: list[PositiveRateMetric] = []
    for field, unit, count in zip(self.TX_FIELDS, self.TX_UNITS, counts[len(self.RX_FIELDS):]):
      metric = PositiveRateMetric(
          measurement=self.MEASUREMENT,
          tags={
              'interface': interface,
              'direction': Directions.TRANSMIT,
              'unit': unit,
          },
          scale_factor=self.SCALE_FACTOR,
          field=field,
      )
      metric.initial_update(count, time_ns)
      tx_metrics.append(metric)

    return rx_metrics + tx_metrics


assert len(NetDev.RX_FIELDS) == len(NetDev.RX_UNITS)
assert len(NetDev.TX_FIELDS) == len(NetDev.TX_UNITS)
