from telegram import Update, BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats
from telegram.ext import CommandHandler, CallbackContext

from core.baseplugin import BasePlugin
from core.plugin import Plugin, handler
from utils.decorators.admins import bot_admins_rights_check
from utils.log import logger


class SetCommandPlugin(Plugin, BasePlugin):

    @handler(CommandHandler, command="set_commands", block=False)
    @bot_admins_rights_check
    async def set_command(self, update: Update, context: CallbackContext):
        user = update.effective_user
        message = update.effective_message
        logger.info("用户 %s[%s] 发出 set_command 命令", user.full_name, user.id)
        user_command = [
            BotCommand("cancel", "取消操作（解决一切玄学问题）"),
            BotCommand("gacha_log_import", "导入抽卡记录"),
            BotCommand("gacha_log_export", "导出抽卡记录"),
            BotCommand("gacha_log_delete", "删除抽卡记录"),
            BotCommand("setuid", "添加/重设UID"),
            BotCommand("setcookie", "添加/重设Cookie"),
            BotCommand("material", "角色培养素材查询"),
            BotCommand("dailynote", "查询实时便笺"),
            BotCommand("ledger", "查询当月旅行札记"),
            BotCommand("abyss_team", "查询深渊推荐配队"),
            BotCommand("avatars", "查询角色练度"),
            BotCommand("gacha_log", "查看抽卡记录"),
            BotCommand("gacha_count", "查看抽卡统计（按卡池）"),
            BotCommand("pay_log", "查看抽卡记录"),
            BotCommand("pay_log_import", "导入抽卡记录"),
            BotCommand("pay_log_export", "导出抽卡记录"),
            BotCommand("pay_log_delete", "删除抽卡记录"),
            BotCommand("sign", "米游社原神每日签到"),
            BotCommand("hilichurls", "丘丘语字典"),
            BotCommand("birthday", "查询角色生日"),
            BotCommand("material", "角色培养素材查询"),
            BotCommand("set_wish", "抽卡模拟器定轨"),
        ]
        group_command = [
            BotCommand("help", "帮助"),
            BotCommand("quiz", "派蒙的十万个为什么"),
            BotCommand("wish", " 非洲人模拟器（抽卡模拟器）"),
            BotCommand("weapon", "查询武器"),
            BotCommand("strategy", "查询角色攻略"),
            BotCommand("stats", "玩家统计查询"),
            BotCommand("daily_material", "今日素材表"),
            BotCommand("player_card", "查询角色卡片"),
            BotCommand("daily_material", "今日素材表"),
        ]
        await context.bot.set_my_commands(commands=group_command, scope=BotCommandScopeAllGroupChats())
        await context.bot.set_my_commands(commands=group_command + user_command,
                                          scope=BotCommandScopeAllPrivateChats())
        await message.reply_text("设置命令成功")
