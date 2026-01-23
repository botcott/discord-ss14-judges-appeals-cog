import os
import json
import logging
import datetime

import discord
from discord.ext import commands

from .data.appeals import (save_data, remove_data, check_appeal, get_judge, 
    get_all_appeals, calc_time, update_time, get_time, get_appeals_info, log_thread_closure, get_thread_logs,
    was_thread_closed, init_db)

with open(f"{os.path.dirname(__file__)}/config/config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

appeal_channel_id = int(cfg["appeal_channel_id"])

async def form(count) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return f"Был найдено {count} обжалование"
    elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
        return f"Было найдено {count} обжалования"
    else:
        return f"Было найдено {count} обжалований"
    
class PaginatedView(discord.ui.View):
    def __init__(self, embeds: list[discord.Embed]):
        super().__init__()
        self.embeds = embeds
        self.current_page = 0
        self.message: discord.WebhookMessage | None = None
        self.update_buttons()

    def update_buttons(self):
        """Обновляет состояние кнопок в зависимости от текущей страницы"""
        self.first_page.disabled = self.current_page == 0
        self.previous_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page == len(self.embeds) - 1
        self.last_page.disabled = self.current_page == len(self.embeds) - 1

    async def on_timeout(self):
        """Прекращает работу после таймаута"""
        for button in self.children:
            button.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except discord.NotFound:
            pass

    @discord.ui.button(label="⏪", style=discord.ButtonStyle.secondary)
    async def first_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.current_page = 0
        self.update_buttons()
        await self.update_embed(interaction)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def previous_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        await self.update_embed(interaction)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.current_page = min(len(self.embeds) - 1, self.current_page + 1)
        self.update_buttons()
        await self.update_embed(interaction)

    @discord.ui.button(label="⏩", style=discord.ButtonStyle.secondary)
    async def last_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.current_page = len(self.embeds) - 1
        self.update_buttons()
        await self.update_embed(interaction)

    @discord.ui.button(label="❌", style=discord.ButtonStyle.red)
    async def stop(self, button: discord.ui.Button, interaction: discord.Interaction):
        """Останавливает пагинацию (удаляет сообщение)"""
        if self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass
            self.message = None
        self.clear_items()

    async def update_embed(self, interaction: discord.Interaction):
        """Обновляет текущий Embed и состояние кнопок"""
        if self.message:
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    async def send(self, ctx):
        """Отправляет первое сообщение и активирует пагинацию"""
        self.update_buttons()
        self.message = await ctx.respond(embed=self.embeds[self.current_page], view=self)

class JudgesAppealsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        init_db()

    @commands.slash_command(name="accept_appeal", description="Принять обжалование")
    async def accept_appeal(self, ctx: discord.ApplicationContext):

        if (not isinstance(ctx.channel, discord.Thread) or ctx.channel.parent_id != appeal_channel_id):
            await ctx.respond("Данная команда работает только в форуме обжалований", ephemeral=True)
            return
        
        if (await check_appeal(ctx.channel_id)):
            await ctx.respond("Данное обжалование уже принято", ephemeral=True)
            return

        thread = self.bot.get_channel(ctx.channel_id)
        
        if (thread.locked == True):
            await ctx.respond(f"Данное обжалование закрыто", ephemeral=True)
            return

        await save_data(ctx.author.id, ctx.channel_id)

        await ctx.respond(f"Обжалование принято судьёй <@{ctx.author.id}>")

    @commands.slash_command(name="close_appeal", description="Закрыть обжалование")
    async def close_appeal(self, ctx: discord.ApplicationContext):

        if (not isinstance(ctx.channel, discord.Thread) or ctx.channel.parent_id != appeal_channel_id):
            await ctx.respond("Данная команда работает только в форуме обжалований", ephemeral=True)
            return
        
        if (await check_appeal(ctx.channel_id) == False):
            await ctx.respond("Данное обжалование ещё не принято", ephemeral=True)
            return
        
        thread = self.bot.get_channel(ctx.channel_id)

        if (thread.locked == True):
            await ctx.respond(f"Данное обжалование закрыто", ephemeral=True)
            return

        await remove_data(ctx.author.id, ctx.channel_id)
        log_thread_closure(
            user_id=ctx.author.id,
            thread_id=thread.id,
            channel_id=appeal_channel_id,
        )

        await ctx.respond(f"Обжалование было закрыто судьёй <@{ctx.author.id}>")
        await thread.edit(archived=True, locked=True)

    @commands.slash_command(name="complaints_stats", description="Список обжалований у пользователя")
    async def complaints_stats(self, ctx: discord.ApplicationContext, member: discord.Member = False):

        if (not member):
            member = ctx.author

        logs = get_thread_logs(user_id=member.id, channel_id=appeal_channel_id)
        
        # Создание embed для пагинации
        embeds = []
        for i in range(0, len(logs), 5):
            log_page = logs[i:i + 5]

            embed = discord.Embed(
                title = f"Статистика закрытых обжалований для {member.display_name}",
                color=discord.Color.blue(),
            )

            for log_item in log_page:
                thread_url = f"https://discord.com/channels/{ctx.guild.id}/{log_item.thread_id}"
                embed.add_field(
                    name=f"Тема: {thread_url}",
                    value=f"Закрыта: {log_item.closed_at.strftime('%Y-%m-%d %H:%M')}",
                    inline=False,
                )
            embed.set_footer(text=f"Общее количество: {len(logs)}")
            embeds.append(embed)

        # Отправка через PaginatedView
        view = PaginatedView(embeds)
        await view.send(ctx)
        
    @commands.Cog.listener()
    async def on_message(self, message):
        if (message.author.id == self.bot.user.id): return
        
        all_appeals = await get_all_appeals()
        
        for appeal in all_appeals:
            judge_id = await get_judge(appeal)
            if message.channel.id == appeal:
                if message.author.id == int(judge_id):
                    await update_time(int(judge_id), int(appeal))

            time = await get_time(int(judge_id), int(appeal))
            now = datetime.datetime.now()
            now_time = now.strftime("%m.%Y.%H.%M.%S")

            seconds = await calc_time(time, now_time)

            if seconds >= 259200: # 3 days
                await update_time(int(judge_id), int(appeal))
                channel = self.bot.get_channel(int(appeal))
                await channel.send(f"Судьи не было более 3-ёх дней, необходим пинг. <@{int(judge_id)}>")