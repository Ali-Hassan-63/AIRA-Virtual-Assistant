# 🤖 AIRA — Artificial Intelligence Response Agent

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg">
  <img src="https://img.shields.io/badge/AI-Voice%20Assistant-purple.svg">
  <img src="https://img.shields.io/badge/GUI-CustomTkinter-green.svg">
  <img src="https://img.shields.io/badge/ML-TF--IDF%20%2B%20Logistic%20Regression-orange.svg">
</p>

<p align="center">
  <b>A modern desktop AI voice assistant built using Python, NLP, Machine Learning, Speech Recognition, and CustomTkinter.</b>
</p>

---

# 🧠 About AIRA

AIRA (Artificial Intelligence Response Agent) is a desktop-based AI virtual assistant developed for the Artificial Intelligence Lab course.

The assistant accepts voice commands through the microphone, predicts user intent using a Machine Learning model, and performs intelligent actions such as:

- 🌦 Weather Updates
- 🔎 Google Search
- 🧮 Calculations
- 🎵 Music Search
- 📚 Wikipedia Summaries
- 📰 Latest News
- 🗺 Google Maps
- 🕒 Time & Date Queries
- 💬 Conversational Responses

The project integrates:

- Natural Language Processing (NLP)
- Machine Learning (ML)
- Speech-to-Text (STT)
- Text-to-Speech (TTS)
- Animated Desktop GUI

---

# ✨ Features

## 🎙 Voice Recognition
- Real-time microphone input
- Continuous listening mode with pause/resume
- Google Speech Recognition API integration

## 🧠 Machine Learning Intent Detection
- TF-IDF Vectorization
- Logistic Regression Classifier
- Confidence threshold handling

## 🔊 Text-to-Speech
- Offline voice synthesis using `pyttsx3`
- Thread-safe TTS engine
- Runtime voice controls

## 🎨 Modern GUI
- Built with `CustomTkinter`
- Animated orb visualizer
- Audio wave animations
- Chat-style interface desktop based GUI

## 🌐 Smart Functionalities
- Live weather updates
- Wikipedia summaries
- Google & YouTube opening
- Calculator
- Maps navigation
- News access

---

# 📁 Project Structure

```bash
AIRA/
│
├── assistant.py
├── interface.py
├── train_model.py
├── intents.csv
├── dataset.csv
├── README.md
│
├── utils/
│   ├── actions.py
│   ├── preprocessing.py
│   ├── speech.py
│   ├── tts.py
│   ├── smart_helpers.py
│
```

---

# ⚙️ Technologies Used

| Technology | Purpose |
|---|---|
| Python 3.11+ | Core Programming Language |
| scikit-learn | Machine Learning Pipeline |
| NLTK | NLP Preprocessing |
| SpeechRecognition | Speech-to-Text |
| pyttsx3 | Offline Text-to-Speech |
| CustomTkinter | Modern GUI |
| requests | API Requests |
| threading | Background Processing |

---

# 🧠 Machine Learning Pipeline

```text
Voice Input
   ↓
Speech-to-Text
   ↓
NLP Preprocessing
   ↓
TF-IDF Vectorization
   ↓
Logistic Regression
   ↓
Intent Prediction
   ↓
Action Execution
   ↓
Voice + GUI Response
```

---

# 📌 Supported Intents

| Intent | Example |
|---|---|
| greeting | "hello" |
| weather | "weather in Lahore" |
| calculator | "calculate 10 plus 5" |
| wikipedia | "who is Albert Einstein" |
| joke | "tell me a joke" |
| play_music | "play music" |
| news | "latest news" |
| open_maps | "open maps" |
| web_search | "search machine learning" |
| help | "what can you do" |
| exit | "goodbye" |

---

# 🚀 Installation

## 1️⃣ Clone Repository

```bash
git clone https://github.com/Ali-Hassan-63/AIRA-Virtual-Assistant
cd AIRA
```

---

## 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔑 API Configuration

## IMPORTANT ⚠️

This project uses external APIs.

Before running the project, replace all placeholder API keys with your own API keys.

### APIs Used

| API | Purpose |
|---|---|
| OpenWeatherMap API | Weather Data |
| Google Speech API | Speech Recognition |
| Wikipedia REST API | Knowledge Summaries |

### Example

```python
WEATHER_API_KEY = "YOUR_API_KEY"
```

---

# ▶️ Running The Project

## Start AIRA GUI

```bash
python interface.py
```

## Train ML Model

```bash
python train_model.py
```

---

# 🧪 Results

| Test | Status |
|---|---|
| Intent Classification | ✅ Working |
| Speech Recognition | ✅ Working |
| TTS Playback | ✅ Working |
| GUI Responsiveness | ✅ Smooth |
| Weather API | ✅ Working |
| Wikipedia Search | ✅ Working |

### Model Performance
- **F1 Score:** `62.4 ± 7.2%`

---

# 🛡 Technical Highlights

- Thread-safe TTS architecture
- Confidence thresholding
- Secure calculator evaluation
- Responsive multi-threaded GUI
- Modular software engineering design

---

# 📚 Future Improvements

- OpenAI/LLM Integration
- Better conversational AI
- Local offline model support
- Smart automation features
- Improved intent dataset
- Enhanced UI animations

---

# 👨‍💻 Developers

## 👤 Syed Ali Hassan
**01-134241-043**

## 👤 Muhammad Ahmad
**01-134241-024**

---

# 🎓 Academic Information

| Field | Details |
|---|---|
| Course | Artificial Intelligence Lab |
| Project | AIRA — Artificial Intelligence Response Agent |
| Language | Python 3.11+ |
| GUI Framework | CustomTkinter |

---

# 📄 License

This project was developed for educational and academic purposes.

---

# ⭐ AIRA

> “Your intelligent desktop voice assistant powered by AI, NLP, and Machine Learning.”
