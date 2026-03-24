import {
  DropdownItem,
  DropdownTrigger,
  Dropdown,
  DropdownMenu,
  Avatar as NextAvatar,
} from '@nextui-org/react';
import { useTranslation } from 'react-i18next';
import { logout } from '@/api';
import { useAccountStore } from '@/stores';

interface AvatarProps {
  name: string;
  email: string;
  avatarUrl: string;
}

export const Avatar = ({ email, name, avatarUrl }: AvatarProps) => {
  const { t } = useTranslation();
  const setAccount = useAccountStore.use.setAccount();
  const handleLogout = async () => {
    setAccount({} as Github.Account);
    await logout();
  };
  return (
    <Dropdown
      placement="bottom-end"
      classNames={{
        content: 'gm-overlay-surface',
      }}
    >
      <DropdownTrigger>
        <NextAvatar
          isBordered
          as="button"
          className="transition-transform"
          color="default"
          size="sm"
          name={name}
          src={avatarUrl}
        />
      </DropdownTrigger>
      <DropdownMenu
        aria-label="Profile Actions"
        variant="flat"
        classNames={{
          base: 'gm-overlay-list',
          list: 'p-1',
        }}
        itemClasses={{
          base: 'gm-overlay-item',
        }}
      >
        <DropdownItem key="profile" className="h-14 gap-2">
          <p className="font-semibold">{name}</p>
          <p className="font-semibold">{email}</p>
        </DropdownItem>
        <DropdownItem key="logout" color="danger" onPress={handleLogout}>
          {t('Log Out')}
        </DropdownItem>
      </DropdownMenu>
    </Dropdown>
  );
};
