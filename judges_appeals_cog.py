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

    @commands.slash_command(name="get_appeals", description="Список обжалований у пользователя")
    async def get_appeals(self, ctx: discord.ApplicationContext, member: discord.Member = False):

        if (not member):
            member = ctx.author

        appeal_info = await get_appeals_info(member.id)

        if appeal_info:
            open_count = len(appeal_info["open_appeals"])
            closed_count = len(appeal_info["closed_appeals"])

            answer = discord.Embed(title=f"Обжалования {member.name}", colour=0x41f096)

            answer.add_field(name="Общее количество", inline=False,
                value=f"{await form(closed_count+open_count)}"
            )
            answer.add_field(name="Открытые обжалования", inline=False,
                value=f"{await form(open_count)}"
            )
            answer.add_field(name="Закрытые обжалования", inline=False,
                value=f"{await form(closed_count)}"
            )

            await ctx.respond(embed=answer, ephemeral=True)
        else:
            await ctx.respond(f"Информация о {member.name} не найдена", ephemeral=True)
    
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