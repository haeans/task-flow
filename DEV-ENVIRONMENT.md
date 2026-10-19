# DEV-ENVIRONMENT

개발 환경 기록. 2026-10-19에 이 PC에서 직접 실행해 확인한 값이다.

## 운영체제와 셸

| 항목 | 값 |
|------|----|
| 운영체제 | Microsoft Windows 11 Pro 10.0.22631 |
| 주 셸 | PowerShell 7.6.7 |
| 보조 셸 | Git Bash (Claude Code의 Bash 도구가 사용. PowerShell 안에서는 `bash` 명령이 인식되지 않음) |

## 도구별 버전

`--version` 실행 결과를 그대로 적었다.

| 도구 | 명령 | 결과 |
|------|------|------|
| git | `git --version` | `git version 2.56.0.windows.2` |
| node | `node --version` | `v24.21.0` |
| npm | `npm --version` | `11.19.0` |
| uv | `uv --version` | `uv 0.13.1 (62faed335 2026-10-13 x86_64-pc-windows-msvc)` |
| python (uv 관리) | `python.exe --version` | `Python 3.12.15` |

python 경로: `C:\Users\EZ\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\python.exe`

**주의**: PATH의 `python`과 `python3`는 Windows Store 안내용 껍데기이다(`C:\Users\EZ\AppData\Local\Microsoft\WindowsApps\`). `python --version`을 실행하면 버전 대신 `Python`만 출력된다. 이 명령은 쓰지 않고 `uv run`으로 실행한다.

## 새로 설치한 것

없음. 위 도구는 모두 이미 설치되어 있었고, 이번 작업에서 설치한 것은 없다.

## 참고

- 요구 버전: Vite는 Node.js 20.19 이상 또는 22.12 이상이 필요하다. 설치된 node v24.21.0은 이를 충족한다.
- `py`, `pip`, `pnpm`, `yarn`, `sqlite3` 명령줄 도구는 없다. 현재 계획에서는 필요하지 않다.
- 화면(React·Vite)과 API(FastAPI) 프로젝트는 아직 만들지 않았다.
