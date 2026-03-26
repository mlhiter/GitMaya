import {
  Navbar as NextUINavbar,
  NavbarContent,
  NavbarMenu,
  NavbarMenuToggle,
  NavbarBrand,
  NavbarItem,
  NavbarMenuItem,
} from '@nextui-org/navbar';
import { Link as NextLink } from '@nextui-org/link';
import { Button } from '@nextui-org/react';

import { siteConfig } from '@/config';
import clsx from 'clsx';
import { GithubIcon, Logo } from '@/components/icons';
import { I18nSwitch } from '@/components/i18n-switch';

import { useTranslation } from 'react-i18next';
import { useAccountStore } from '@/stores';
import { Avatar } from '@/components/avatar';
import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom';

export const Navbar = () => {
  const account = useAccountStore.use.account();
  const getAccount = useAccountStore.use.updateAccount();
  const navigate = useNavigate();
  const location = useLocation();

  const { t } = useTranslation();

  const login = async () => {
    await getAccount();
    navigate('/app/people');
  };

  return (
    <NextUINavbar
      maxWidth="xl"
      position="sticky"
      className="gm-nav"
      classNames={{
        wrapper: 'px-4 sm:px-6',
      }}
    >
      <NavbarContent className="basis-1/5 sm:basis-full" justify="start">
        <NavbarBrand as="li" className="max-w-fit">
          <RouterLink className="flex items-center gap-3" to="/">
            <Logo />
            <div className="gm-brand text-lg sm:text-xl font-bold text-[#f2e8cf]">GitMaya</div>
          </RouterLink>
        </NavbarBrand>
        <ul className="hidden lg:flex gap-2 justify-start ml-3">
          {siteConfig.navItems.map((item) => {
            const active = location.pathname === item.href;
            return (
              <NavbarItem key={item.href}>
                <RouterLink
                  className={clsx(
                    'rounded-full px-3 py-1.5 text-sm font-semibold transition-colors',
                    active
                      ? 'gm-chip'
                      : 'text-[var(--gm-text-muted)] hover:text-[var(--gm-text-main)]',
                  )}
                  to={item.href}
                >
                  {t(item.label)}
                </RouterLink>
              </NavbarItem>
            );
          })}
        </ul>
      </NavbarContent>

      <NavbarContent className="hidden sm:flex basis-1/5 sm:basis-full" justify="end">
        <NavbarItem className="hidden sm:flex gap-3">
          <NextLink isExternal href={siteConfig.links.github} aria-label="Github">
            <GithubIcon className="text-[#d9d4c7] hover:text-[#f6d27c] transition-colors" />
          </NextLink>
          <I18nSwitch />
        </NavbarItem>
        <NavbarItem className="hidden sm:flex">
          {account ? (
            <Avatar
              name={account.user?.name}
              email={account.user?.email}
              avatarUrl={account.user?.avatar}
            />
          ) : (
            <Button
              onPress={login}
              className="gm-primary-btn rounded-full px-5 h-10 min-w-28 text-sm"
            >
              {t('Sign in')}
            </Button>
          )}
        </NavbarItem>
      </NavbarContent>

      <NavbarContent className="sm:hidden basis-1 pl-4" justify="end">
        <NextLink isExternal href={siteConfig.links.github} aria-label="Github">
          <GithubIcon className="text-[#d9d4c7]" />
        </NextLink>
        <NavbarMenuToggle />
      </NavbarContent>

      <NavbarMenu className="pt-5">
        <div className="mx-2 flex flex-col gap-2">
          {siteConfig.navMenuItems.map((item) => (
            <NavbarMenuItem key={item.href}>
              <RouterLink
                className={clsx(
                  'block rounded-xl px-3 py-2 text-base font-semibold',
                  location.pathname === item.href
                    ? 'gm-chip'
                    : 'text-[var(--gm-text-main)]/85 hover:bg-white/5',
                )}
                to={item.href}
              >
                {t(item.label)}
              </RouterLink>
            </NavbarMenuItem>
          ))}
        </div>
      </NavbarMenu>
    </NextUINavbar>
  );
};
