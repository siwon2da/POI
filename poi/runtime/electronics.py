"""전자·Arduino 연구용 표준 모듈.

직렬 통신은 선택 의존성인 ``pyserial`` 을 사용한다. 실제 보드가 없어도
``electronics.mock()`` 으로 센서/출력 코드를 테스트할 수 있다.
"""
from __future__ import annotations

import time as _time
from types import SimpleNamespace

from ..errors import POIError
from .boxes import boxify


def _serial_module():
    try:
        import serial  # type: ignore
        import serial.tools.list_ports  # type: ignore
        return serial
    except ImportError:
        raise POIError(
            "Arduino 직렬 통신에 pyserial이 필요합니다.", "P370",
            hint="설치: pip install pyserial\n보드 없이 연습: electronics.mock()")


def _ports():
    serial = _serial_module()
    return [boxify({
        "device": p.device,
        "name": p.name,
        "description": p.description,
        "manufacturer": p.manufacturer or "",
        "vid": p.vid,
        "pid": p.pid,
    }) for p in serial.tools.list_ports.comports()]


class SerialBoard:
    """줄 단위 명령을 주고받는 Arduino/마이크로컨트롤 연결."""

    def __init__(self, port, baud=115200, timeout=1.0, settle=2.0):
        serial = _serial_module()
        try:
            self._serial = serial.Serial(str(port), int(baud),
                                         timeout=float(timeout))
            if settle:
                _time.sleep(float(settle))
                self._serial.reset_input_buffer()
        except Exception as e:
            raise POIError(f"직렬 포트를 열 수 없습니다 ({port}): {e}", "P371",
                           hint="electronics.ports()로 포트 이름을 확인하세요.")
        self.port = str(port)
        self.baud = int(baud)

    @property
    def is_open(self):
        return bool(self._serial.is_open)

    def write(self, data):
        raw = data if isinstance(data, (bytes, bytearray)) else str(data).encode("utf-8")
        return self._serial.write(bytes(raw))

    def write_line(self, text):
        return self.write(str(text).rstrip("\r\n") + "\n")

    def read_line(self):
        return self._serial.readline().decode("utf-8", "replace").rstrip("\r\n")

    def query(self, command):
        self.write_line(command)
        return self.read_line()

    def digital_write(self, pin, value):
        return self.query(f"DWRITE {int(pin)} {1 if bool(value) else 0}")

    def pwm_write(self, pin, value):
        value = max(0, min(255, int(value)))
        return self.query(f"PWM {int(pin)} {value}")

    def analog_read(self, pin):
        reply = self.query(f"AREAD {int(pin)}")
        try:
            return int(reply.split()[-1])
        except (ValueError, IndexError):
            raise POIError(f"센서 응답을 숫자로 읽을 수 없습니다: {reply!r}", "P372")

    def close(self):
        self._serial.close()
        return True

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()

    def __repr__(self):
        return f"<ArduinoSerial {self.port} @{self.baud}>"


class MockBoard:
    """하드웨어가 없는 CI/수업 환경용 결정적 가상 보드."""

    def __init__(self, analog=None):
        self.analog = {int(k): int(v) for k, v in dict(analog or {}).items()}
        self.digital = {}
        self.pwm = {}
        self.history = []
        self.is_open = True
        self.port = "mock"
        self.baud = 0

    def write_line(self, text):
        self.history.append(str(text))
        return len(str(text)) + 1

    def read_line(self):
        return "OK"

    def query(self, command):
        self.write_line(command)
        parts = str(command).split()
        if parts[:1] == ["AREAD"] and len(parts) >= 2:
            return str(self.analog.get(int(parts[1]), 0))
        return "OK"

    def digital_write(self, pin, value):
        self.digital[int(pin)] = bool(value)
        self.query(f"DWRITE {int(pin)} {1 if bool(value) else 0}")
        return "OK"

    def pwm_write(self, pin, value):
        value = max(0, min(255, int(value)))
        self.pwm[int(pin)] = value
        self.query(f"PWM {int(pin)} {value}")
        return "OK"

    def analog_read(self, pin):
        return int(self.query(f"AREAD {int(pin)}"))

    def set_analog(self, pin, value):
        self.analog[int(pin)] = int(value)
        return value

    def close(self):
        self.is_open = False
        return True


def _voltage(raw, reference=5.0, bits=10):
    maximum = (1 << int(bits)) - 1
    if maximum <= 0:
        raise POIError("ADC 비트 수는 1 이상이어야 합니다.", "P373")
    return float(raw) * float(reference) / maximum


def _adc(volts, reference=5.0, bits=10):
    maximum = (1 << int(bits)) - 1
    if float(reference) <= 0:
        raise POIError("기준 전압은 0보다 커야 합니다.", "P373")
    return max(0, min(maximum, round(float(volts) / float(reference) * maximum)))


def _ohm(voltage=None, current=None, resistance=None):
    values = [voltage is not None, current is not None, resistance is not None]
    if sum(values) != 2:
        raise POIError("전압(voltage), 전류(current), 저항(resistance) 중 두 값을 주세요.", "P374")
    if voltage is None:
        return float(current) * float(resistance)
    if current is None:
        return float(voltage) / float(resistance)
    return float(voltage) / float(current)


def _parallel(values):
    vals = [float(v) for v in values]
    if not vals or any(v <= 0 for v in vals):
        raise POIError("병렬 저항값은 모두 0보다 커야 합니다.", "P374")
    return 1.0 / sum(1.0 / v for v in vals)


def _sample(board, pin, count=10, interval=0.05):
    out = []
    for index in range(int(count)):
        out.append(board.analog_read(pin))
        if interval and index + 1 < int(count):
            _time.sleep(float(interval))
    return out


electronics = SimpleNamespace(
    ports=_ports,
    connect=lambda port, baud=115200, timeout=1.0, settle=2.0:
        SerialBoard(port, baud, timeout, settle),
    arduino=lambda port, baud=115200, timeout=1.0, settle=2.0:
        SerialBoard(port, baud, timeout, settle),
    mock=lambda analog=None: MockBoard(analog),
    voltage=_voltage,
    adc=_adc,
    ohm=_ohm,
    series=lambda values: sum(float(v) for v in values),
    parallel=_parallel,
    divider=lambda vin, r1, r2: float(vin) * float(r2) / (float(r1) + float(r2)),
    sample=_sample,
    SerialBoard=SerialBoard,
    MockBoard=MockBoard,
)

# 짧은 영문 별칭. POI 코드에서는 둘 다 use std:... 로 쓸 수 있다.
arduino = electronics
hardware = electronics

__all__ = ["electronics", "arduino", "hardware", "SerialBoard", "MockBoard"]
