"""Paste into YOUR existing discord.py bot. The library only handles phone <-> bot communication.

You store {user_id: {"license": ..., "trigger_url": ...}} however you like (DB/json).
License is a secret: collect it with a Modal (not a slash-command argument) and reply ephemeral.
"""
import discord
from phoneip import RotateError, is_valid_license, check_trigger_url, rotate_with_license

users = {}  # replace with your own storage


class RegisterModal(discord.ui.Modal, title="라이센스 등록"):
    license = discord.ui.TextInput(label="폰에서 나온 라이센스", min_length=24, max_length=60)
    trigger = discord.ui.TextInput(label="Pushcut URL (아이폰만)", required=False)

    async def on_submit(self, i: discord.Interaction):
        key, url = self.license.value.strip(), self.trigger.value.strip() or None
        if not is_valid_license(key) or (url and not check_trigger_url(url)):
            return await i.response.send_message("라이센스/URL 형식 오류", ephemeral=True)
        users[i.user.id] = {"license": key, "trigger_url": url}
        await i.response.send_message("등록 완료", ephemeral=True)


# in your View:
@discord.ui.button(label="IP 바꾸기", style=discord.ButtonStyle.primary, custom_id="phoneip:rotate")
async def change(self, i: discord.Interaction, button: discord.ui.Button):
    u = users.get(i.user.id)
    if not u:
        return await i.response.send_message("먼저 라이센스를 등록하세요", ephemeral=True)
    await i.response.defer(ephemeral=True)
    try:
        ip = await rotate_with_license(u["license"], u["trigger_url"])   # <- the only call you need
        await i.followup.send(f"새 IP: `{ip}`", ephemeral=True)
    except RotateError as e:
        await i.followup.send(f"실패: {e}", ephemeral=True)
