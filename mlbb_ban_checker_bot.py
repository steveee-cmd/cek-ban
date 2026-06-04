"""
MLBB Ban Checker Bot untuk Telegram
Requirements: pip install python-telegram-bot requests
Cara pakai: Isi BOT_TOKEN, lalu jalankan script ini
"""

import logging
import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# ─── CONFIG ───────────────────────────────────────────────
BOT_TOKEN = "8206213420:AAFT4fI9ICNrCdx57W1VDcmNTDhac3pUpVI"

# Endpoint API resmi Moonton (dipakai game MLBB itu sendiri)
MLBB_API_URL = "https://api.mobilelegends.com/base/v1.1/community/user/checkPlayer"

# State untuk ConversationHandler
WAITING_USER_ID, WAITING_ZONE_ID = range(2)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─── FUNGSI CEK BANNED ────────────────────────────────────
def check_mlbb_account(user_id: str, zone_id: str) -> dict:
    """
    Cek status akun MLBB via API Moonton.
    Return dict berisi info akun atau error.
    """
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    payload = {
        "userID": user_id,
        "zoneID": zone_id,
    }

    try:
        response = requests.post(
            MLBB_API_URL,
            json=payload,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        # Response sukses dari Moonton biasanya: {"code": 0, "data": {...}}
        if data.get("code") == 0 and data.get("data"):
            account_data = data["data"]
            return {
                "success": True,
                "username": account_data.get("username") or account_data.get("name", "Tidak ditemukan"),
                "user_id": user_id,
                "zone_id": zone_id,
                "is_banned": account_data.get("isBlocked", False)
                             or account_data.get("banned", False),
                "raw": account_data,
            }
        else:
            # Code selain 0 = akun tidak ditemukan / ID salah
            return {
                "success": False,
                "error": f"Akun tidak ditemukan. Pastikan User ID dan Zone ID benar. (code: {data.get('code')})",
            }

    except requests.exceptions.Timeout:
        return {"success": False, "error": "⏱ Request timeout. Server MLBB lambat, coba lagi."}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "🌐 Gagal koneksi ke server MLBB."}
    except requests.exceptions.HTTPError as e:
        return {"success": False, "error": f"HTTP Error: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Error tidak terduga: {e}"}


def format_result(result: dict) -> str:
    """Format hasil pengecekan menjadi pesan Telegram."""
    if not result["success"]:
        return f"❌ *Gagal mengecek akun*\n\n{result['error']}"

    status_emoji = "🔴 BANNED" if result["is_banned"] else "🟢 AKTIF / TIDAK BANNED"
    divider = "─" * 30

    msg = (
        f"📋 *Hasil Cek Akun MLBB*\n"
        f"{divider}\n"
        f"👤 *Username* : `{result['username']}`\n"
        f"🆔 *User ID* : `{result['user_id']}`\n"
        f"🌐 *Zone ID* : `{result['zone_id']}`\n"
        f"⚡ *Status* : *{status_emoji}*\n"
        f"{divider}\n"
    )

    if result["is_banned"]:
        msg += "⚠️ Akun ini terdeteksi *BANNED* oleh Moonton.\n"
    else:
        msg += "✅ Akun ini *AMAN* dan tidak dalam status banned.\n"

    msg += "\n_Hasil berdasarkan data real-time dari server Moonton._"
    return msg


# ─── HANDLER TELEGRAM ─────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 *Selamat datang di MLBB Ban Checker Bot!*\n\n"
        "Gunakan perintah:\n"
        "• `/cek <UserID> <ZoneID>` — Cek langsung\n"
        "• `/panduan` — Cara menemukan User ID & Zone ID\n\n"
        "Contoh: `/cek 123456789 1234`",
        parse_mode="Markdown",
    )


async def panduan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 *Cara Menemukan User ID & Zone ID*\n\n"
        "1. Buka game Mobile Legends\n"
        "2. Tap foto profil kamu di pojok kiri atas\n"
        "3. User ID & Zone ID tertera di bawah nama akunmu\n"
        "   Format: `(ID) (Zone)`\n\n"
        "Contoh: ID `123456789` Zone `1234`\n\n"
        "Lalu gunakan: `/cek 123456789 1234`",
        parse_mode="Markdown",
    )


async def cek_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk /cek <UserID> <ZoneID>"""
    args = context.args

    if len(args) != 2:
        await update.message.reply_text(
            "⚠️ Format salah!\n\nGunakan: `/cek <UserID> <ZoneID>`\nContoh: `/cek 123456789 1234`",
            parse_mode="Markdown",
        )
        return

    user_id, zone_id = args[0], args[1]

    if not user_id.isdigit() or not zone_id.isdigit():
        await update.message.reply_text("❌ User ID dan Zone ID harus berupa angka!")
        return

    msg = await update.message.reply_text("🔍 Sedang mengecek akun, mohon tunggu...")

    result = check_mlbb_account(user_id, zone_id)
    formatted = format_result(result)

    await msg.edit_text(formatted, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🤖 *MLBB Ban Checker Bot*\n\n"
        "Perintah tersedia:\n"
        "• `/start` — Mulai bot\n"
        "• `/cek <UserID> <ZoneID>` — Cek status banned\n"
        "• `/panduan` — Cara cari User ID & Zone ID\n"
        "• `/help` — Tampilkan bantuan ini",
        parse_mode="Markdown",
    )


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "❓ Perintah tidak dikenal. Ketik /help untuk melihat daftar perintah."
    )


# ─── MAIN ─────────────────────────────────────────────────
def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("panduan", panduan))
    app.add_handler(CommandHandler("cek", cek_command))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("✅ Bot MLBB Ban Checker berjalan...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
