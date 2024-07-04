import streamlit as st
from audio_recorder_streamlit import audio_recorder
from openai import OpenAI
from tempfile import NamedTemporaryFile
import base64
import streamlit.components.v1 as components
import time

# Streamlit Secrets から API キーを取得
api_key = st.secrets.get("OPENAI_API_KEY", "")

# サイドバーでAPIキーを入力できるようにする（オプション）
api_key = st.sidebar.text_input("OpenAI API Key", type="password", value=api_key, key="api_key_input")

# OpenAI クライアントの初期化
client = OpenAI(api_key=api_key)

# セッション状態の初期化
if 'audio_bytes_japanese' not in st.session_state:
    st.session_state.audio_bytes_japanese = None
if 'audio_bytes_english' not in st.session_state:
    st.session_state.audio_bytes_english = None
if 'messages_japanese' not in st.session_state:
    st.session_state.messages_japanese = []
if 'messages_english' not in st.session_state:
    st.session_state.messages_english = []

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
def text_to_speech(text):
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text
    )
    return response.content

# -------------------------------------------------------
# 関数名
# autoplay_audio
# 
# 引数
# audio_content：バイナリ形式の音声データ
# 
# 概要
# Base64エンコードされた音声データを自動再生するHTMLとJavaScriptを生成し、
# Streamlitコンポーネントとして表示する
# -------------------------------------------------------
def autoplay_audio(audio_content):
    # バイナリ形式の音声データをBase64エンコードされた文字列に変換
    audio_base64 = base64.b64encode(audio_content).decode('utf-8')
    # 音声再生
    components.html(
        f"""
        <script>
        const audio = new Audio("data:audio/mp3;base64,{audio_base64}");
        audio.play();
        </script>
        """,
        height=0,
    )

# -------------------------------------------------------
# 関数名
# process_audio
# 
# 引数
# audio_bytes：バイト形式の音声データ
# source_lang：音声の元の言語
# target_lang：翻訳先の言語
# 
# 概要
# 音声データを処理し、メッセージの翻訳と音声再生を行う
# -------------------------------------------------------
def process_audio(audio_bytes, source_lang, target_lang):

    # 録音時間が短すぎる場合（例：1秒未満）の処理
    if len(audio_bytes) < 16000:  # 16kHzのサンプリングレートを仮定
        st.warning("録音時間が短すぎます。もう一度お試しください。")
        return
        
    # 音声をテキストに変換
    transcript = transcribe_audio(audio_bytes)
    
    # メッセージの重複をチェック
    messages = st.session_state.messages_japanese if source_lang == "Japanese" else st.session_state.messages_english
    if not messages or messages[-1]['content'] != transcript:
        with st.spinner("処理中..."):
            translated_text = translate_text(transcript, target_lang)
        
            # 新しいメッセージオブジェクトを作成
            new_message = {
                "content": transcript,
                "translated": translated_text,
                "timestamp": time.time()
            }
            # メッセージリストに新しいメッセージを追加
            messages.append(new_message)

            # 翻訳されたテキストを音声に変換
            audio_content = text_to_speech(translated_text)

            # 音声を自動再生
            autoplay_audio(audio_content)

# アプリのタイトル
st.title("音声翻訳アプリ")

if 'messages' not in st.session_state:
    st.session_state.messages = []

st.write("※マイクアイコンが表示されない場合はReloadボタンを押してください。")
st.button("Reload")

# レコーダーを横並びに配置
col1, col2 = st.columns(2)

# 日本語レコーダの処理
with col1:
    st.write("Japanese")
    audio_bytes_japanese = audio_recorder(
        pause_threshold=2.0,
        recording_color="#e8b62c",
        neutral_color="#6aa36f",
        icon_name="microphone",
        icon_size="5x",
        key="recorder_1"
    )

    if audio_bytes_japanese:
        st.session_state.audio_bytes_japanese = audio_bytes_japanese
        process_audio(st.session_state.audio_bytes_japanese, "Japanese", "English")

# 英語レコーダの処理
with col2:
    st.write("English")
    audio_bytes_english = audio_recorder(
        pause_threshold=2.0,
        recording_color="#e8b62c",
        neutral_color="#3498db",
        icon_name="microphone",
        icon_size="5x",
        key="recorder_2"
    )

    if audio_bytes_english:
        st.session_state.audio_bytes_english = audio_bytes_english
        process_audio(st.session_state.audio_bytes_english, "English", "Japanese")

# メッセージ表示エリア
st.markdown("""
<style>
.message-container { display: flex; margin-bottom: 20px; align-items: flex-start; }
.message-container.left { justify-content: flex-start; }
.message-container.right { justify-content: flex-end; }
.message-box-wrapper {
    max-width: 80%;
    display: flex;
    flex-direction: column;
}
.message-box-wrapper.right {
    align-items: flex-end;
}
.message-box {
    word-wrap: break-word;
    padding: 10px;
    border-radius: 10px;
    margin: 5px 0;
    border: 1px solid #ddd;
    max-width: 100%;
}
.japanese-message { background-color: #ffffff; color: #333333; }
.english-message { background-color: #ffffff; color: #333333; }
.translation.japanese { background-color: #e6f7ff; color: #333333; }
.translation.english { background-color: #e6ffe6; color: #333333; }
</style>
""", unsafe_allow_html=True)

# 日本語と英語のメッセージを時系列順にマージ
all_messages = sorted(
    [(msg, 'japanese') for msg in st.session_state.messages_japanese] +
    [(msg, 'english') for msg in st.session_state.messages_english],
    key=lambda x: x[0].get('timestamp', 0)
)

# メッセージ表示(時系列順に表示、言語別に左右に表示)
for i, (msg, lang) in enumerate(all_messages):
    align = 'left' if lang == 'japanese' else 'right'
    message_class = 'japanese-message' if lang == 'japanese' else 'english-message'
    translation_class = 'english' if lang == 'japanese' else 'japanese'
     
    st.markdown(f"""
    <div class="message-container {align}">
        <div class="message-box-wrapper {align}">
            <div class="message-box {message_class}">{msg['content']}</div>
            <div class="message-box translation {translation_class}">{msg['translated']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 翻訳音声
    col1, col2 = st.columns(2)
    
    if lang == 'japanese':
        with col1:
            audio_content = text_to_speech(msg['translated'])
            audio_base64 = base64.b64encode(audio_content).decode('utf-8')
            audio_tag = f'<audio controls><source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3"></audio>'
            st.markdown(audio_tag, unsafe_allow_html=True)
    else:
        with col2:
            audio_content = text_to_speech(msg['translated'])
            audio_base64 = base64.b64encode(audio_content).decode('utf-8')
            audio_tag = f'<audio controls><source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3"></audio>'
            st.markdown(audio_tag, unsafe_allow_html=True)