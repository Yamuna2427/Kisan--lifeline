import json
import os
import re
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="Telugu Kisan Lifeline")

DATA_FILE = Path(__file__).parent / "approved_qa.json"


def normalize(text):
    text = text.strip().lower()
    text = re.sub(r"[^\w\s\u0C00-\u0C7F]", " ", text)
    return re.sub(r"\s+", " ", text)


def get_answer(question):
    # Only approved database records are allowed.
    with open(DATA_FILE, encoding="utf-8") as f:
        records = json.load(f)

    question = normalize(question)

    for item in records:
        if item.get("approved") is not True:
            continue

        phrases = [item["question_te"]] + item.get("aliases_te", [])

        if any(question == normalize(p) for p in phrases):
            return {
                "status": "answered",
                "answer": item["answer_te"],
                "source": item["source"]
            }

    return {
        "status": "refer",
        "answer": (
            "క్షమించండి. మా ఆమోదించిన డేటాబేస్‌లో "
            "ఈ ప్రశ్నకు ధృవీకరించిన సమాధానం లేదు. "
            "దయచేసి వ్యవసాయ నిపుణుడిని సంప్రదించండి."
        ),
        "source": None
    }


class Question(BaseModel):
    question: str


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!doctype html>
    <html lang="te">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>తెలుగు కిసాన్ లైఫ్‌లైన్</title>
      <style>
        body { font-family: sans-serif; max-width: 700px;
          margin: 25px auto; padding: 15px; line-height: 1.6; }
        textarea { width: 100%; height: 90px; font-size: 17px; }
        button { padding: 12px; margin: 6px 4px 6px 0; }
        .card { border: 1px solid #ccc; border-radius: 12px;
          padding: 15px; margin-top: 15px; }
      </style>
    </head>
    <body>
      <h1>తెలుగు కిసాన్ లైఫ్‌లైన్ 🌾</h1>
      <p>మీ వ్యవసాయ ప్రశ్నను తెలుగులో అడగండి.</p>

      <div class="card">
        <textarea id="q" placeholder="మీ ప్రశ్న ఇక్కడ రాయండి"></textarea>
        <br>
        <button onclick="listen()">🎙️ మాట్లాడండి</button>
        <button onclick="ask()">సమాధానం</button>
        <button onclick="speak()">🔊 వినండి</button>
      </div>

      <div class="card">
        <h3 id="status">సిద్ధంగా ఉంది</h3>
        <p id="answer">మీ ప్రశ్న కోసం వేచి ఉంది.</p>
        <small id="source"></small>
      </div>

      <script>
        let lastAnswer = "";

        async function ask() {
          const question = document.getElementById("q").value.trim();
          if (!question) {
            document.getElementById("status").textContent =
              "దయచేసి ప్రశ్న అడగండి.";
            return;
          }

          document.getElementById("status").textContent =
            "డేటాబేస్‌లో వెతుకుతోంది...";

          try {
            const response = await fetch("/ask", {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({question})
            });

            const data = await response.json();
            lastAnswer = data.answer;
            document.getElementById("answer").textContent = data.answer;
            document.getElementById("source").textContent =
              data.source ? "మూలం: " + data.source :
              "ధృవీకరించిన సమాచారం లేదు.";
            document.getElementById("status").textContent =
              data.status === "answered" ?
              "డేటాబేస్ సమాధానం" : "నిపుణుడిని సంప్రదించండి";
          } catch (error) {
            document.getElementById("status").textContent =
              "సర్వర్ అందుబాటులో లేదు.";
            document.getElementById("answer").textContent =
              "సేవ విఫలమైంది. మళ్లీ ప్రయత్నించండి.";
          }
        }

        function listen() {
          const SR = window.SpeechRecognition ||
                     window.webkitSpeechRecognition;

          if (!SR) {
            alert("ఈ browser లో voice input లేదు. ప్రశ్న టైప్ చేయండి.");
            return;
          }

          const recognition = new SR();
          recognition.lang = "te-IN";
          recognition.onresult = event => {
            document.getElementById("q").value =
              event.results[0][0].transcript;
          };
          recognition.start();
        }

        function speak() {
          if (!lastAnswer) return;
          if (!window.speechSynthesis) {
            alert("ఈ device లో speech output లేదు.");
            return;
          }

          const speech = new SpeechSynthesisUtterance(lastAnswer);
          speech.lang = "te-IN";
          window.speechSynthesis.cancel();
          window.speechSynthesis.speak(speech);
        }
      </script>
    </body>
    </html>
    """


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
def ask(payload: Question):
    if not payload.question.strip():
        return {"status": "refer", "answer": "దయచేసి ప్రశ్న అడగండి.",
                "source": None}
    return get_answer(payload.question)
