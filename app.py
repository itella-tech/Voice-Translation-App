import streamlit as st
from audio_recorder_streamlit import audio_recorder
import os
from dotenv import load_dotenv
from openai import OpenAI
from tempfile import NamedTemporaryFile
import base64
import openai

# Streamlit Secrets から API キーを取得
openai.api_key = st.secrets["OPENAI_API_KEY"]

# OpenAI APIキーの設定
api_key = st.sidebar.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY") or "", key="api_key_input")
client = OpenAI(api_key=api_key)

# -------------------------------------------------------
# 関数名
# transcribe_audio
# 
# 引数
# audio_bytes：バイト形式の音声データ
# 
# 概要
# 音声データ（バイト形式）を一時ファイルに保存し、
# OpenAIのWhisper APIを使用して音声をテキストに変換
# -------------------------------------------------------
def transcribe_audio(audio_bytes):
    # 一時ファイルを作成し音声データを書き込み
    with NamedTemporaryFile(delete=True, suffix=".wav") as temp_audio_file:
        temp_audio_file.write(audio_bytes)
        temp_audio_file.flush()
        
        # 音声をテキストに変換
        with open(temp_audio_file.name, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
    return transcript.text

# -------------------------------------------------------
# 関数名
# translate_text
# 
# 引数
# text：翻訳したい元のテキスト
# target_lang：翻訳先の言語
# 
# 概要
# 入力されたテキストを指定された言語に翻訳
# -------------------------------------------------------
def translate_text(text, target_lang):
    # GPT-3.5-turboモデルにリクエストを送信
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that translates text."},
            {"role": "user", "content": f"Translate the following text to {target_lang}: {text}"}
        ],
        max_tokens=1000,
        n=1,
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()

# -------------------------------------------------------
# 関数名
# text_to_speech
# 
# 引数
# text： 音声に変換したいテキスト
# voice：使用する音声タイプ（デフォルトは"alloy"）
# 
# 概要
# OpenAIのTTS APIを使用して、テキストを高品質な音声に変換
# -------------------------------------------------------
def text_to_speech(text, voice="alloy"):
    response = client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text
    )
    return response.content

# アプリのタイトル
st.title("音声録音、文字起こし、翻訳、音声出力")

# 録音用のプレースホルダー
audio_placeholder = st.empty()

# セッション状態の初期化
if 'target_lang' not in st.session_state:
    st.session_state.target_lang = "English"
if 'audio_bytes' not in st.session_state:
    st.session_state.audio_bytes = None

# 翻訳先言語の選択
new_target_lang = st.radio("翻訳先言語を選択してください", ["English", "Japanese"])

# 言語が変更された場合、audio_bytesをリセット
if new_target_lang != st.session_state.target_lang:
    st.session_state.target_lang = new_target_lang
    st.session_state.audio_bytes = None
    st.experimental_rerun()

# 音声の選択
# voice = st.selectbox("音声を選択してください", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])
voice = "alloy"

st.write("※マイクアイコンが表示されない場合はReloadボタンを押してください。")
st.button("Reload")

# 音声録音
st.write("以下のマイクアイコンをクリックして録音を開始してください。")
audio_bytes = audio_recorder(
    pause_threshold=2.0,
    recording_color="#e8b62c",
    neutral_color="#6aa36f",
    icon_name="microphone",
    icon_size="5x",
)

# 音声が録音された場合の処理
if audio_bytes:
    st.audio(audio_bytes, format="audio/wav")
    
    with st.spinner("処理中..."):
        # 音声をテキストに変換
        transcript = transcribe_audio(audio_bytes)
        st.success("文字起こしが完了しました")
        st.write(transcript)
        
        # テキストを翻訳
        translated_text = translate_text(transcript,  st.session_state.target_lang)
        st.subheader("翻訳結果:")
        st.write(translated_text)
        
        # 翻訳テキストを音声に変換
        audio_content = text_to_speech(translated_text)
        
        # 翻訳テキストを音声に変換
        audio_content = text_to_speech(translated_text, voice)
        
        # 音声の再生（自動再生付き）
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        audio_tag = f'<audio id="audio" autoplay><source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3"></audio>'
        st.markdown(audio_tag, unsafe_allow_html=True)

        # JavaScript for autoplay
        st.markdown(
            """
            <script>
                var audio = document.getElementById("audio");
                audio.play();
            </script>
            """,
            unsafe_allow_html=True
        )

        # 音声をStreamlitで再生可能な形式に変換
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        audio_tag = f'<audio controls><source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3"></audio>'
        st.markdown(audio_tag, unsafe_allow_html=True)