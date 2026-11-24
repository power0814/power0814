# 목소리 데이터셋 추출기

방송·영상에서 한 사람의 목소리만 깨끗하게 잘라 TTS·음성 변환 학습용 데이터셋을 만든다. 출력은 GPT-SoVITS `.list`와 LJSpeech `metadata.csv` 형식이다.

옥냥이 AI용으로 만들었다. 본인이 2차 창작에 동의한 범위 안에서 쓴다.

```
download    yt-dlp로 오디오만 받기 (채널·재생목록·치지직 다시보기 URL)
reference   본인 목소리만 나오는 클립 → 기준 목소리 벡터
process     10분씩 끊어서
              Demucs로 목소리/배경음 분리
              Silero VAD로 발화 단위(1.5–12초) 자르기
              품질 거르기: 너무 작음 · 찢어짐 · 배경음이 큼 · 청크 경계에 걸림
              ECAPA 화자 유사도로 다른 사람 거르기 (합방 게스트, 게임 캐릭터, 도네 TTS)
transcribe  faster-whisper large-v3로 받아쓰기
export      최종 기준으로 다시 걸러 wav + 대본 내보내기
```

단계마다 결과가 `work/`에 남는다. 중간에 끊겨도 다시 돌리면 끝난 영상은 건너뛴다. 영상을 더 받은 뒤 `process`부터 다시 돌리면 새 영상만 처리한다.

## 설치

NVIDIA GPU가 있는 PC를 권장한다. CPU로도 돌아가지만 분리와 받아쓰기가 실시간보다 느리다.

```bash
# Python 3.10 이상, ffmpeg 필요
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cu124   # 자기 CUDA 버전에 맞게
pip install -r requirements.txt
```

처음 돌릴 때 Demucs, ECAPA(Hugging Face), Whisper 모델을 자동으로 내려받는다.

## 쓰는 법

모든 명령은 이 폴더에서 `python -m vds ...`로 돌린다. 작업 폴더는 기본이 `./work`이고 `--work`로 바꿀 수 있다.

### 1. 기준 목소리

`ref/` 폴더에 **본인 목소리만** 나오는 클립을 넣는다.

- 합 3–5분이면 충분하다. 클립 수는 상관없다.
- 합방, 도네이션 TTS, 게임 대사가 섞인 부분은 빼야 한다. 배경음은 괜찮다(같이 분리한다).

```bash
python -m vds reference ref/
```

중심과의 유사도 최소값이 0.4 아래로 나오면 다른 목소리가 섞인 클립이 있다는 뜻이다.

### 2. 받기

```bash
# 채널의 동영상 탭 전체 (노래 영상은 제목으로 거름)
python -m vds download "<채널 URL>/videos" --reject-title "노래|커버|cover|MV|ASMR"

# 다시보기 탭
python -m vds download "<채널 URL>/streams"

# URL 목록 파일
python -m vds download -a urls.txt
```

- 받은 영상은 `work/archive.txt`에 적혀 다시 받지 않는다.
- 이미 갖고 있는 파일(다시보기 녹화본 등)은 `work/raw/`에 넣거나, `process --input <폴더>`로 지정한다.
- 연령 제한·멤버십 영상은 `--cookies-from-browser chrome`을 붙인다.
- 저장 공간은 원본 오디오 1시간에 약 60 MB가 든다.

### 3. 처리

```bash
python -m vds process
```

영상마다 진행률과 속도(실시간 대비 몇 배)를 찍는다. 여기서는 기준을 느슨하게 걸어 일단 저장하고, 엄격한 기준은 5단계에서 건다. 그래서 기준을 바꿔도 이 단계를 다시 돌릴 필요가 없다.

- `--demucs-model htdemucs_ft`: 분리가 더 깨끗하지만 약 4배 느리다.
- `--separator none`: 배경음이 없는 원본이면 분리를 건너뛴다.

### 4. 받아쓰기

```bash
python -m vds transcribe
python -m vds transcribe --model large-v3-turbo          # 더 빠르게
python -m vds transcribe --initial-prompt "옥냥이, 냥이, ..."   # 고유명사 표기 맞추기
```

### 5. 내보내기

먼저 `--dry-run`으로 몇 시간이 남는지와 버린 이유를 본다.

```bash
python -m vds export --speaker okyangi --dry-run
```

```
후보 N개 (X시간) → 남김 M개 (Y시간)
  버림 speaker          ...
  버림 low_confidence   ...
  화자 유사도 분포 (5/25/50/75/95%): [...]
```

이상 없으면 실제로 내보낸다.

```bash
python -m vds export --speaker okyangi --sr 44100
```

`work/dataset/`에 다음이 생긴다.

| 파일 | 내용 |
|---|---|
| `wavs/*.wav` | 모노 16비트, 음량을 −20 dBFS로 맞춘 구간 |
| `okyangi.list` | GPT-SoVITS 형식 `경로\|화자\|ko\|대본` |
| `metadata.csv` | LJSpeech 형식 `이름\|대본` |
| `summary.json` | 남은 시간, 버린 이유별 개수, 적용한 기준 |
| `audit/` | 화자 기준선(`--min-sim`) 근처 구간 40개. 파일 이름이 `유사도_keep/drop_...` |

`audit/`을 들어 보고 기준을 정한다.

- `drop`인데 본인 목소리가 많으면 `--min-sim`을 내린다.
- `keep`인데 다른 사람이 섞여 있으면 올린다.

### 최종 기준

| 옵션 | 기본 | 버리는 것 |
|---|---|---|
| `--min-sim` | 0.55 | 기준 목소리와 다른 화자 |
| `--max-bgm-db` | −15 | 배경음이 목소리보다 15 dB 이내로 큰 구간 (분리 잔여물 위험) |
| `--min-logprob` | −0.8 | Whisper가 자신 없어한 구간 (웅얼거림, 겹친 말) |
| `--max-no-speech` | 0.6 | 말이 아닌 소리 |
| `--max-same-text` | 20 | 같은 문장은 이만큼까지만 |
| (고정) | | 웃음만 있는 구간(ㅋㅋ, 하하), Whisper 환각 문장("시청해 주셔서 감사합니다" 등), 초당 글자 수가 1.5–12를 벗어난 구간 |

화자 중심은 기본으로 다시 잡는다. 기준 클립과 확실히 같은 깨끗한 구간이 50개 이상 모이면 그 평균을 새 중심으로 쓴다. 끄려면 `--no-refine`.

## 양에 대해

많이 모을수록 좋은 건 학습 방식에 따라 다르다.

- **GPT-SoVITS, RVC 같은 미세 조정:** 깨끗한 1–10시간이면 충분하다. 양을 늘리기보다 `--min-sim`, `--max-bgm-db`, `--min-logprob`를 올려 상위 품질만 쓰는 게 낫다.
- **처음부터 학습하는 TTS:** 수십 시간 이상이 도움이 된다. 이때는 기준을 기본값 정도로 두고 양을 늘린다.

어느 쪽이든 `work/`는 그대로 두고 `export`만 기준을 바꿔 여러 벌 뽑을 수 있다(`--out`으로 폴더를 나눈다).

## 거르지 못하는 것

- **노래:** 본인이 부르면 화자 필터를 통과한다. 노래 영상은 `--reject-title`로 빼고, 방송 중 노래 구간은 `low_confidence`·`speech_rate`로 일부만 걸러진다.
- **겹친 말:** 본인 목소리가 주도하고 다른 사람이 작게 섞인 구간은 화자 유사도가 높게 나올 수 있다. `--min-logprob`을 올리면 줄어든다.
- **편집 영상의 효과음:** 분리 후에도 잔여물이 남을 수 있다. 다시보기 원본이 편집본보다 깨끗한 경우가 많다.

## 테스트

```bash
pip install pytest
python -m pytest tests
```

합성 음성과 가짜 화자 모델로 전체 흐름을 확인한다. 분리 → 자르기 → 다른 화자 거르기 → 받아쓰기 → 내보내기 순이다. 모델 가중치는 받지 않는다.
