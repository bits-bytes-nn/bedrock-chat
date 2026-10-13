import i18n from 'i18next';

const PREFIX = 'bot.shareDialog.label.sharing';

export const getShareText = (userCount: number, groupCount: number): string => {
  if (userCount === 0 && groupCount === 0) {
    return i18n.t(`${PREFIX}.not_shared`);
  }

  const users = i18n.t(`${PREFIX}.user_count`, { count: userCount });
  const groups = i18n.t(`${PREFIX}.group_count`, { count: groupCount });
  if (userCount > 0 && groupCount > 0) {
    return i18n.t(`${PREFIX}.shared_both`, { users, groups });
  }
  return i18n.t(`${PREFIX}.shared_with`, {
    target: userCount > 0 ? users : groups,
  });
};
