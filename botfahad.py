from telegram import Update, ChatPermissions, ChatMember
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext
from collections import defaultdict

# قائمة الكلمات الممنوعة
blocked_words = set()

# تخزين المعلومات
banned_users = set()
restricted_users = set()
warnings = defaultdict(list)
user_messages = defaultdict(int)  # تغيير إلى عداد
admins = {1279032954}  # معرّف المدير الرئيسي
moderators = set()  # قائمة المشرفين
members_set = set()  # لتخزين معرفات الأعضاء

# دالة للتحقق من ما إذا كان المستخدم عضوًا
def is_member(update: Update) -> bool:
    user_id = update.effective_user.id
    return user_id not in admins and user_id not in moderators

# دالة للتحقق إذا كان المستخدم مديرًا أو مشرفًا
def is_user_admin(update: Update) -> bool:
    return update.effective_user.id in admins or update.effective_user.id in moderators

# دالة لقفل الدردشة
def lock_chat(update: Update, context: CallbackContext) -> None:
    if is_user_admin(update):
        permissions = ChatPermissions(can_send_messages=False)
        context.bot.set_chat_permissions(update.effective_chat.id, permissions=permissions)
        context.bot.send_message(chat_id=update.effective_chat.id, text="🔒 تم قفل الدردشة.")

# دالة لفتح الدردشة
def unlock_chat(update: Update, context: CallbackContext) -> None:
    if is_user_admin(update):
        permissions = ChatPermissions(can_send_messages=True)
        context.bot.set_chat_permissions(update.effective_chat.id, permissions=permissions)
        context.bot.send_message(chat_id=update.effective_chat.id, text="🔓 تم فتح الدردشة،"
                                                                        " بإمكان الأعضاء المشاركة الآن.")

# دالة لمنع الكلمات
def block_word(update: Update, context: CallbackContext) -> None:
    if is_user_admin(update):
        words_to_block = update.message.text.split()[1:]  # استخرج الكلمات بعد الأمر
        if words_to_block:
            for word in words_to_block:
                blocked_words.add(word.lower())  # إضافة الكلمات المحظورة للقائمة
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"تم منع الكلمات: {'، '.join(words_to_block)}")
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text="يرجى تحديد الكلمات المراد منعها.")

# دالة إظهار الكلمات المحظورة
def show_blocked_words(update: Update, context: CallbackContext) -> None:
    """إظهار الكلمات المحظورة داخل البوت."""
    if blocked_words:
        # عرض الكلمات المحظورة
        blocked_list = "\n".join(blocked_words)
        update.message.reply_text(f"الكلمات المحظورة حاليًا:\n{blocked_list}")
    else:
        # في حال عدم وجود كلمات محظورة
        update.message.reply_text("لا توجد كلمات محظورة حاليًا.")


# دالة لإلغاء منع الكلمة
def unblock_word(update: Update, context: CallbackContext) -> None:
    if is_user_admin(update):
        words_to_unblock = update.message.text.split()[1:]  # استخرج الكلمات بعد الأمر
        if words_to_unblock:
            for word in words_to_unblock:
                blocked_words.discard(word.lower())  # إزالة الكلمات من القائمة
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"تم إلغاء منع الكلمات: {'، '.join(words_to_unblock)}")
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text="يرجى تحديد الكلمات المراد إلغاء منعها.")

# دالة للتحقق من الرسائل لمنع الكلمات
def check_blocked_words(update: Update, context: CallbackContext) -> None:
    if is_member(update):  # فقط الأعضاء يتعرضون للفحص
        message_text = update.message.text.lower()
        for word in blocked_words:
            if word in message_text:  # تحقق إذا كانت الكلمة المحظورة موجودة في النص
                context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
                return



# دالة للحصول على المستخدم من المنشن أو الرد على الرسالة
def get_user_by_mention_or_reply(update: Update, context: CallbackContext):
    message = update.message

    # إذا كانت الرسالة هي رد على رسالة أخرى
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        return user.id, user.username if user.username else user.first_name

    # محاولة استخراج المستخدم من الكيانات
    entities = message.entities
    if entities:
        for entity in entities:
            if entity.type == "mention":
                username = message.text[entity.offset + 1: entity.offset + entity.length]
                try:
                    chat_member: ChatMember = context.bot.get_chat_member(update.effective_chat.id, username)
                    user = chat_member.user
                    return user.id, user.username if user.username else user.first_name
                except Exception as e:
                    context.bot.send_message(chat_id=update.effective_chat.id,
                                             text=f"🚫 المستخدم @{username} غير موجود في المجموعة.")
                    return None, None
            elif entity.type == "text_mention":  # معالجة الكيانات التي تحتوي على نص منشن
                user = entity.user
                return user.id, user.username if user.username else user.first_name

    context.bot.send_message(chat_id=update.effective_chat.id, text="🚫 لم يتم العثور على مستخدم.")
    return None, None


# دالة لمنع استخدام أوامر معينة على المدير أو المشرفين
def cannot_target_admin_or_moderator(user_id: int) -> bool:
    return user_id in admins or user_id in moderators

# دالة لحظر المستخدم
def ban(update: Update, context: CallbackContext) -> None:
    if is_user_admin(update):
        user_id, username = get_user_by_mention_or_reply(update, context)
        if user_id:
            if cannot_target_admin_or_moderator(user_id):
                context.bot.send_message(chat_id=update.effective_chat.id, text="عذرا ليس لديك الرتبة المناسبة لفعل ذلك.")
                return
            banned_users.add(user_id)
            context.bot.kick_chat_member(update.effective_chat.id, user_id)
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"تم حظر @{username}.")

# دالة لفك الحظر
def unban(update: Update, context: CallbackContext) -> None:
    if is_user_admin(update):
        user_id, username = get_user_by_mention_or_reply(update, context)
        if user_id and user_id in banned_users:
            banned_users.remove(user_id)
            context.bot.unban_chat_member(update.effective_chat.id, user_id)
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"تم فك حظر @{username}.")


from telegram import ChatPermissions
from telegram.ext import CallbackContext

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# دالة لتقييد المستخدم
def restrict(update: Update, context: CallbackContext) -> None:
    if not is_user_admin(update):
        return  # إذا لم يكن المستخدم مشرفًا، لا يفعل شيئًا
    user_id, username = get_user_by_mention_or_reply(update, context)
    if not user_id or cannot_target_admin_or_moderator(user_id):
        return  # إذا لم يكن هناك مستخدم مستهدف أو إذا كان المستخدم مستهدفًا لديه رتبة أعلى

    # التحقق من وجود args لتحديد المدة
    duration_seconds = None
    if context.args is not None and len(context.args) >= 2:
        # محاولة استخراج القيمة والوحدة من المدخلات
        try:
            time_value = int(context.args[0])
            time_unit = context.args[1].lower()

            # تحديد المدة الزمنية بالثواني
            if time_unit in ["دقيقة", "دقائق"]:
                if 1 <= time_value <= 30:  # الحد الأدنى والأقصى لدقائق
                    duration_seconds = time_value * 60
            elif time_unit in ["ساعة", "ساعات"]:
                if 1 <= time_value <= 720:  # 720 ساعة = 30 يوم
                    duration_seconds = time_value * 3600
            elif time_unit in ["يوم", "أيام"]:
                if 1 <= time_value <= 30:  # الحد الأدنى والأقصى للأيام
                    duration_seconds = time_value * 86400  # 24 ساعة = 86400 ثانية

        except ValueError:
            return  # تجاهل إذا كانت القيمة ليست عددًا صحيحًا

    # إضافة المستخدم إلى قائمة التقييد
    restricted_users.add(user_id)
    permissions = ChatPermissions(can_send_messages=False)
    context.bot.restrict_chat_member(update.effective_chat.id, user_id, permissions=permissions)

    # إعداد الزر الشفاف
    keyboard = [[InlineKeyboardButton("القوانين", url="https://t.me/c/2088812510/1337")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # إذا كانت المدة محددة، قم بتحديد مدة انتهاء التقييد
    if duration_seconds is not None:
        context.job_queue.run_once(release_user, duration_seconds, context=(update.effective_chat.id, user_id))
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"تم تقييد @{username} لمدة {time_value} {time_unit}.",
                                 reply_markup=reply_markup)  # إضافة الزر هنا
    else:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"تم تقييد @{username} بشكل دائم حتى يتم فك التقييد.",
                                 reply_markup=reply_markup)  # إضافة الزر هنا

def release_user(context: CallbackContext):
    chat_id, user_id = context.args
    # إعادة السماح للمستخدم بالتحدث
    permissions = ChatPermissions(can_send_messages=True)
    context.bot.restrict_chat_member(chat_id, user_id, permissions=permissions)
    context.bot.send_message(chat_id=chat_id, text=f"✅ تم إنهاء التقييد للمستخدم {user_id}.")

def unrestrict_user(context: CallbackContext):
    chat_id, user_id, username = context.job.context
    restricted_users.discard(user_id)  # إزالة المستخدم من قائمة المقيّدين
    permissions = ChatPermissions(can_send_messages=True)
    context.bot.restrict_chat_member(chat_id, user_id, permissions=permissions)
    context.bot.send_message(chat_id=chat_id, text=f"تم فك التقييد عن @{username}.")


# دالة لفك القيد
def unrestrict(update: Update, context: CallbackContext) -> None:
    if is_user_admin(update):
        user_id, username = get_user_by_mention_or_reply(update, context)
        if user_id and user_id in restricted_users:
            restricted_users.remove(user_id)
            permissions = ChatPermissions(can_send_messages=True)
            context.bot.restrict_chat_member(update.effective_chat.id, user_id, permissions=permissions)
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"تم فك تقييد @{username}.")


from telegram import InlineKeyboardButton, InlineKeyboardMarkup


# دالة لإعطاء إنذار مع عداد الإنذارات
def warn(update: Update, context: CallbackContext) -> None:
    if is_user_admin(update):
        user_id, username = get_user_by_mention_or_reply(update, context)
        if user_id:
            if cannot_target_admin_or_moderator(user_id):
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text="عذرا ليس لديك الرتبة المناسبة لفعل ذلك.")
                return

            warnings[user_id].append("Warning")
            current_warnings = len(warnings[user_id])

            # إعداد الزر الشفاف
            keyboard = [[InlineKeyboardButton("القوانين", url="https://t.me/c/2088812510/1337")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f'🚨 الإنذار [{current_warnings} من 3] لـ @{username}، التزم بقوانين المجموعة.',
                reply_markup=reply_markup  # إضافة الزر هنا
            )

            if current_warnings >= 3:
                restrict(update, context)
                # حذف جميع الإنذارات
                warnings[user_id] = []  # مسح جميع الإنذارات بعد التقييد


# دالة لمسح إنذار
def delete_warning(update: Update, context: CallbackContext) -> None:
    if is_user_admin(update):
        user_id, username = get_user_by_mention_or_reply(update, context)
        if user_id and warnings[user_id]:
            warnings[user_id].pop()  # حذف آخر إنذار
            current_warnings = len(warnings[user_id])
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"تم مسح إنذار لـ @{username}. عدد الإنذارات الحالية: [{current_warnings} من 3]."
            )
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"لا يوجد إنذارات لـ @{username}.")


from telegram import InlineKeyboardButton, InlineKeyboardMarkup


# دالة لمسح الرسالة المحددة
def delete_message(update: Update, context: CallbackContext) -> None:
    if is_user_admin(update):
        if update.message.reply_to_message:
            context.bot.delete_message(chat_id=update.effective_chat.id,
                                       message_id=update.message.reply_to_message.message_id)
            # إعداد الزر الشفاف
            keyboard = [[InlineKeyboardButton("القوانين", url="https://t.me/c/2088812510/1337")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="تم حذف الرسالة المحددة.",
                                     reply_markup=reply_markup)  # إضافة الزر هنا


# دالة لترقية أو تنزيل رتبة المستخدم
def promote_or_demote(update: Update, context: CallbackContext) -> None:
    if is_user_admin(update):
        user_id, username = get_user_by_mention_or_reply(update, context)
        if user_id:
            command_text = update.message.text.split()
            if len(command_text) > 1:
                role = command_text[1].lower()
                if role == "مشرف":
                    moderators.add(user_id)
                    context.bot.promote_chat_member(update.effective_chat.id, user_id, can_change_info=True, can_delete_messages=True, can_restrict_members=True)
                    context.bot.send_message(chat_id=update.effective_chat.id, text=f"تم ترقية @{username} إلى مشرف.")
                elif role == "عضو":
                    moderators.discard(user_id)
                    context.bot.promote_chat_member(update.effective_chat.id, user_id, can_change_info=False, can_delete_messages=False, can_restrict_members=False)
                    context.bot.send_message(chat_id=update.effective_chat.id, text=f"تم تنزيل @{username} إلى عضو.")
                else:
                    context.bot.send_message(chat_id=update.effective_chat.id, text="الرتبة غير صحيحة، يرجى استخدام مشرف أو عضو.")
            else:
                context.bot.send_message(chat_id=update.effective_chat.id, text="يرجى تحديد الرتبة (مشرف أو عضو).")


from telegram import InlineKeyboardButton, InlineKeyboardMarkup


# دالة للحصول على معلومات المستخدم
def reveal_user_info(update: Update, context: CallbackContext) -> None:
    if is_user_admin(update):
        user_id, username = get_user_by_mention_or_reply(update, context)
        if user_id:
            message_count = user_messages[user_id]
            user_status = "مدير" if user_id in admins else "مشرف" if user_id in moderators else "عضو"
            user_name_display = context.bot.get_chat(user_id).first_name  # الحصول على الاسم المعروض في حساب تيليجرام
            user_mention = f"<a href='tg://user?id={user_id}'>{user_name_display}</a>"
            current_warnings = len(warnings.get(user_id, []))  # الحصول على عدد الإنذارات الحالية للمستخدم

            # بناء رسالة المعلومات
            info_message = (
                f"👤 اسم المستخدم: {user_name_display}\n"  # استخدام الاسم المعروض بدلاً من اسم المستخدم
                f"🆔 رمـــز المعـــرف: <code>{user_id}</code>\n"  # جعل الرمز قابلاً للنسخ
                f"🌐 منشن المستخدم: {user_mention}\n"
                f"🔰 حالة المستخدم: {user_status}\n"
                f"📊 عـدد الرســائــل: <code>{message_count}</code>\n"  # جعل العدد قابلاً للنسخ
            )

            # إضافة عدد الإنذارات إذا كانت أكبر من صفر
            if current_warnings > 0:
                info_message += f"⚠️ عدد الإنذارات: {current_warnings} من 3"  # إضافة عدد الإنذارات

            # إعداد الزر الشفاف
            keyboard = [[InlineKeyboardButton("اه خوذ", url="https://t.me/c/2088812510/1343")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            context.bot.send_message(chat_id=update.effective_chat.id, text=info_message, parse_mode='HTML',
                                     reply_markup=reply_markup)  # إضافة الزر هنا


# دالة للتعامل مع النصوص
def handle_text(update: Update, context: CallbackContext):
    if is_member(update):
        # التحقق من الكلمات المحظورة حتى من الأعضاء
        check_blocked_words(update, context)
        return  # تجاهل الرسائل من الأعضاء


    message = update.message.text
    user_id = update.message.from_user.id
    user_messages[user_id] += 1  # زيادة عدد الرسائل

    # التحقق من الأوامر المكتوبة باللغة العربية
    if message.startswith("حظر"):
        ban(update, context)
    elif message.startswith("فك حظر"):
        unban(update, context)
    elif message.startswith("تقييد"):
        restrict(update, context)
    elif message.startswith("فك قيد"):
        unrestrict(update, context)
    elif message.startswith("إنذار"):
        warn(update, context)
    elif message.startswith("مسح إنذار"):
        delete_warning(update, context)
    elif message.startswith("حذف"):
        delete_message(update, context)
    elif message.startswith("كشف"):
        reveal_user_info(update, context)
    elif message.startswith("جعله") and is_user_admin(update):
        promote_or_demote(update, context)
    elif message.startswith("منع"):
        block_word(update, context)
    elif message.startswith("إلغاء منع"):
        unblock_word(update, context)
    elif message.startswith("الكلمات الممنوعة"):
        show_blocked_words(update, context)  # استدعاء دالة إظهار الكلمات الممنوعة
    elif message.startswith("قفل الدردشة"):
        lock_chat(update, context)
    elif message.startswith("فتح الدردشة"):
        unlock_chat(update, context)
    else:
        check_blocked_words(update, context)


# إعداد البوت
def main() -> None:
    updater = Updater("7849134428:AAGtZo3sn_D2f-DkZhr0MAYQ1ORkzXJB7sM", use_context=True)
    dp = updater.dispatcher

    # التعامل مع النصوص
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
