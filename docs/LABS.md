# POI 전자·Arduino·보안 연구실

POI 1.16은 실제 장치가 없어도 실험을 작성하고 검증한 뒤 Arduino와 연결할 수 있는
`electronics` 모듈과, 허가된 환경에서 방어 보안 기초를 연구하는 `security` 모듈을 제공합니다.

## Arduino와 전자

보드 없이 시작:

```poi
board = electronics.mock()
board.set_analog(0, 512)
raw = board.analog_read(0)
show electronics.voltage(raw, 5.0, 10)
board.digital_write(13, true)
```

실제 보드 연결:

1. `pip install pyserial`
2. Arduino IDE에서 `examples/arduino/poi_bridge.ino`를 보드에 업로드
3. `electronics.ports()`로 포트 확인
4. `electronics.arduino("COM3", 115200)`로 연결

```poi
board = electronics.arduino("COM3", 115200)
show board.analog_read(0)
board.pwm_write(9, 128)
board.close()
```

주요 API:

- `electronics.ports()` — 연결된 직렬 장치 목록
- `electronics.arduino(port, baud, timeout, settle)` — 줄 단위 직렬 연결
- `digital_write`, `pwm_write`, `analog_read`, `query`, `write_line`, `read_line`
- `voltage`, `adc`, `ohm`, `series`, `parallel`, `divider`, `sample`
- `electronics.mock()` — 장치 없는 수업·CI용 가상 보드

Arduino 이외의 ESP32, Raspberry Pi Pico, micro:bit도 같은 줄 단위 프로토콜을
구현하면 연결할 수 있습니다.

## 방어 보안 연구

```poi
show security.sha256("evidence")
show security.entropy("sample bytes")
show security.password_report("example-only!42")
show security.scan_ports("127.0.0.1", [22, 80, 443])
```

주요 API:

- `hash`, `sha256`, `file_hash`, `hmac`, `constant_equal`
- `entropy`, `password_report`, `analyze_headers`
- `port_open`, `scan_ports`, `private_target`

### 안전 제한

- 네트워크 점검은 기본적으로 loopback·사설망·link-local 주소만 허용합니다.
- 한 호출에서 최대 256개 포트, 연결 제한 시간 최대 2초, 동시 작업 최대 32개입니다.
- 공개 주소는 **본인 소유 또는 명시적 허가를 받은 경우에만** 호출의
  `allow_public=true`와 환경변수 `POI_SECURITY_ALLOW_PUBLIC=1`을 함께 지정해야 합니다.
- 이 모듈은 침입, 자격 증명 탈취, 악성 코드 배포 기능을 제공하지 않습니다.

전체 예제는 `examples/arduino_serial.poi`와 `examples/security_lab.poi`에 있습니다.
