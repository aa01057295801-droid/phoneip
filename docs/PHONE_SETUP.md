# 폰 설치 가이드 (라이센스 방식)

흐름:

```
디스코드 버튼 -> 봇이 트리거 전송 -> 폰이 에어플레인 모드 ON/OFF -> 폰이 새 IP를 ntfy로 회신 -> 봇이 표시
```

**라이센스** = 폰이 만든 랜덤 비밀 문자열(`PIP-xxxxxxxxxxxxxxxxxxxxxxxx`).
봇과 폰이 이 문자열에서 같은 비공개 ntfy 토픽을 계산하므로 서버를 따로 둘 필요가 없습니다.
**비밀번호처럼 취급하세요.** 아는 사람은 폰을 조작할 수 있고 IP를 볼 수 있습니다.

---

## Android (추천 - 가장 안정적)

1. F-Droid 에서 **Termux** 설치 (Play 스토어 버전은 오래됨).
2. Termux 에서:
   ```
   pkg install python git
   pip install git+https://github.com/YOURNAME/phoneip.git   # 또는 압축 푼 폴더에서 pip install .
   phoneip agent
   ```
3. 처음 실행하면 화면에 `LICENSE: PIP-...` 가 출력됩니다. 이걸 디스코드 봇의 **라이센스 등록**에 붙여넣기.
   (`~/.phoneip_license` 에 저장되어 다음부터 같은 라이센스를 씁니다)
4. 에어플레인 모드를 켜고 끌 **권한**이 필요합니다. 아래 중 하나:
   - **루팅된 폰**: `phoneip agent` 가 자동으로 `su` 를 씁니다.
   - **루팅 없음**: 개발자 옵션 > **무선 디버깅** 켜기 > `pkg install android-tools` >
     `adb pair localhost:<페어링포트>` > `adb connect localhost:<연결포트>`.
     `adb devices` 에 폰이 보이면 에이전트가 자동으로 adb 를 씁니다. (폰 재부팅 시 다시 연결 필요)
5. 배터리 최적화에서 Termux 제외, Termux 알림의 **Acquire wakelock** 켜기.
6. 에이전트는 기본으로 **Wi-Fi 를 끕니다.** (Wi-Fi 가 켜져 있으면 통신사 IP 가 아니라 Wi-Fi IP 가 나옴.)
   Wi-Fi 를 유지하려면 `--keep-wifi` (이 경우 보고되는 IP 는 Wi-Fi 쪽일 수 있음).

---

## iPhone (단축어 + Pushcut)

iOS 는 앱이 에어플레인 모드를 직접 켤 수 없고, 백그라운드에서 계속 도는 에이전트도 못 둡니다.
그래서 **단축어(Shortcuts) + Pushcut Automation Server(유료 Pro)** 가 사실상 유일한 방법입니다.
그리고 아래 조건을 지켜야 안정적입니다:

- Pushcut 앱의 **Automation Server** 를 켜 두기 (앱이 살아 있어야 함, 충전기 연결 권장)
- 폰 **저전력 모드 끄기**, Pushcut 에 백그라운드 새로고침 허용
- 잠금 상태에서 에어플레인 모드 단축어가 막히는 iOS 버전이 있을 수 있음 -> 먼저 직접 실행해서 확인

### 1) 단축어 `RotateIP` 만들기

처음 실행하면 라이센스를 만들어 보여주고, 이후에는 IP 를 바꿉니다.

1. **파일(Files)** 또는 **메모** 말고 단축어 자체에 저장하려면: 단축어 앱 > `RotateIP` 새로 만들기.
2. 라이센스 확보:
   - `Get File` (iCloud Drive > Shortcuts > `phoneip_license.txt`, "Error if Not Found" 끄기)
   - `If` *파일 있음 아님(Does Not Have Any Value)* 이면:
     - `Get Contents of URL`:
       `https://www.random.org/strings/?num=1&len=24&digits=on&upperalpha=on&loweralpha=on&unique=off&format=plain&rnd=new`
     - `Text`: `PIP-` + 위 결과 (공백/줄바꿈 제거: `Replace Text` 로 `\n` -> 빈칸)
     - `Save File` 로 `phoneip_license.txt` 저장 (덮어쓰기)
     - `Show Result` 로 라이센스 표시 + `Copy to Clipboard`  <- **이게 봇에 넣을 라이센스**
     - `Stop This Shortcut`
   - `End If`
   - (random.org 가 막히면 `Ask for Input` 으로 직접 만든 20~48자 영숫자를 받아 `PIP-` 를 붙여도 됩니다.)
3. IP 변경 동작 (라이센스가 이미 있을 때):
   1. `Get Contents of URL` -> `https://ntfy.sh/pip-r-<라이센스 본문>` Method **POST**, Body 텍스트 `ack`
      (봇이 "폰이 명령을 받았다"를 알 수 있게 함. `<라이센스 본문>` = `PIP-` 뒤의 24자)
   2. `Set Wi-Fi` **Off**   <- 중요: Wi-Fi 가 켜져 있으면 Wi-Fi 의 IP 가 나옵니다
   3. `Set Airplane Mode` **On**
   4. `Wait` 3초
   5. `Set Airplane Mode` **Off**
   6. `Set Wi-Fi` **Off** (에어플레인 해제 때 Wi-Fi 가 되살아날 수 있음)
   7. `Wait` 10초
   8. `Get Contents of URL` -> `https://api.ipify.org`  (실패하면 `Wait` 5초 후 한 번 더)
   9. `Get Contents of URL` -> `https://ntfy.sh/pip-r-<라이센스 본문>` Method **POST**, Body = 8번 결과
      (실패 시 Body `error: no network` 를 보내면 봇이 바로 실패를 표시합니다)
4. 처음 한 번은 단축어를 **직접 실행**해서 권한 팝업(허용)을 모두 승인하세요.

### 2) Pushcut 트리거 URL

1. Pushcut > **Automation Server** 켜기.
2. Pushcut 의 Web API 화면에서 `RotateIP` 실행 URL 복사:
   `https://api.pushcut.io/<API_KEY>/execute?shortcut=RotateIP`
3. 디스코드 봇 **라이센스 등록** 창에 라이센스와 이 URL 을 함께 입력.
   (봇은 `https://api.pushcut.io/` 로 시작하는 URL 만 허용합니다)

> 한계: iOS 는 백그라운드/잠금 상태에서 단축어 실행이 OS 업데이트마다 달라질 수 있습니다.
> 안 될 때는 Pushcut 앱이 켜져 있는지, 폰이 잠금 해제 상태에서 되는지부터 확인하세요.
> 안정성이 중요하면 Android 를 쓰는 편이 낫습니다.

---

## 봇 쪽

봇은 직접 돌리시는 것을 쓰고, `examples/bot_snippet.py` 의 `rotate_with_license(license, trigger_url)` 한 줄만 호출하면 됩니다.
`pip install phoneip` 외에 서버/포트 개방이 필요 없습니다 (봇 호스트 -> ntfy.sh <- 폰).
