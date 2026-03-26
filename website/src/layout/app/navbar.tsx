import {
  Navbar as NextUINavbar,
  NavbarContent,
  NavbarMenu,
  NavbarMenuToggle,
  NavbarBrand,
  NavbarItem,
  NavbarMenuItem,
} from '@nextui-org/navbar';

import { link as linkStyles } from '@nextui-org/theme';

import clsx from 'clsx';
import { GithubIcon, Logo, LarkWhiteIcon } from '@/components/icons';
// import { ThemeSwitch } from '@/components/theme-switch';
import { I18nSwitch } from '@/components/i18n-switch';

import { useTranslation } from 'react-i18next';
import { Link as RouterLink, useNavigate, useLocation } from 'react-router-dom';
import { useAccountStore, useTeamInfoStore } from '@/stores';
import { Avatar } from '@/components/avatar';

import { appSiteConfig } from '@/config/app';

import useSwr from 'swr';

import { getTeams, switchTeam } from '@/api';

import {
  Select,
  SelectItem,
  Link,
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  Button,
  useDisclosure,
} from '@nextui-org/react';
import { useEffect, useMemo } from 'react';
import useSWRMutation from 'swr/mutation';
import { isNull } from 'lodash-es';

export const Navbar = () => {
  const { t } = useTranslation();
  const location = useLocation();
  const { isOpen, onOpen, onOpenChange, onClose } = useDisclosure();
  const navigate = useNavigate();
  const account = useAccountStore.use.account();
  const updateAccount = useAccountStore.use.updateAccount();
  const getTeamInfo = useTeamInfoStore.use.updateTeamInfo();
  const teamInfo = useTeamInfoStore.use.teamInfo();

  const team_id = account?.current_team as string;

  useEffect(() => {
    if (team_id) {
      getTeamInfo(team_id);
    }
  }, [team_id, getTeamInfo]);

  const { trigger } = useSWRMutation(
    `api/account`,
    (
      _url,
      {
        arg,
      }: {
        arg: {
          current_team: string;
        };
      },
    ) => switchTeam(arg),
  );

  const { data } = useSwr('/api/team', getTeams);

  const teams =
    useMemo(
      () =>
        data?.data
          .map((item) => ({
            label: item.name,
            value: item.id,
          }))
          .concat({
            label: t('Create a new team'),
            value: 'create',
          }),
      [data?.data, t],
    ) || [];

  const selectTeam = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const team_id = e.target.value;
    if (team_id === 'create') {
      navigate('/app/induction');
    } else {
      await trigger({
        current_team: team_id,
      });
      updateAccount();
      navigate('/app/people', { replace: true });
    }
  };

  const shouldShowOnboarding = useMemo(() => {
    const onInductionPage = location.pathname === '/app/induction';
    return !onInductionPage && (isNull(teamInfo?.im_application) || isNull(account?.current_team));
  }, [account?.current_team, location.pathname, teamInfo?.im_application]);

  useEffect(() => {
    if (shouldShowOnboarding) {
      setTimeout(onOpen, 1000);
    }
  }, [onOpen, shouldShowOnboarding]);

  const onboarding = () => {
    onClose();
    navigate('/app/induction');
  };

  return (
    <>
      <NextUINavbar
        maxWidth="xl"
        position="sticky"
        className="gm-nav"
        classNames={{
          wrapper: 'px-4 sm:px-6',
        }}
      >
        <NavbarContent className="basis-1/5 sm:basis-full" justify="start">
          <NavbarBrand as="li" className="gap-3 max-w-fit">
            <Link className="flex justify-start items-center gap-1" href="/">
              <Logo />
              <div className="gm-brand text-lg sm:text-xl font-bold mx-4 text-[#f2e8cf]">GitMaya</div>
            </Link>
          </NavbarBrand>
          <ul className="hidden lg:flex gap-2 justify-start ml-2">
            {appSiteConfig.navItems.map((item) => (
              <NavbarItem key={item.href}>
                <Link
                  className={clsx(
                    linkStyles({ color: 'foreground' }),
                    'rounded-full px-3 py-1.5 text-sm font-semibold text-[var(--gm-text-muted)] hover:text-[var(--gm-text-main)] data-[active=true]:bg-white/10 data-[active=true]:text-[var(--gm-text-main)]',
                  )}
                  color="foreground"
                  href={item.href}
                >
                  {t(item.label)}
                </Link>
              </NavbarItem>
            ))}
          </ul>
        </NavbarContent>
        {shouldShowOnboarding && (
          <NavbarContent className="basis-1/5 sm:basis-full" justify="center">
            <Button onPress={onboarding} variant="bordered">
              {t("Complete your team's onboarding...")}
            </Button>
          </NavbarContent>
        )}
        <NavbarContent className="hidden sm:flex basis-1/5 sm:basis-full" justify="end">
          <NavbarItem className="hidden sm:flex">
            <Select
              label={t('Select a team')}
              className="max-w-xs min-w-48"
              size="sm"
              classNames={{
                trigger: 'gm-overlay-trigger',
                label: 'gm-overlay-label',
                value: 'gm-overlay-value',
                selectorIcon: 'text-[var(--gm-text-muted)]',
                popoverContent: 'gm-overlay-surface p-1',
                listboxWrapper: 'gm-overlay-list',
                listbox: 'gm-overlay-list',
              }}
              onChange={selectTeam}
              selectedKeys={[team_id]}
              items={teams}
              disallowEmptySelection
            >
              {(team) => (
                <SelectItem key={team.value} value={team.value} className="gm-overlay-item">
                  {team.label}
                </SelectItem>
              )}
            </Select>
          </NavbarItem>
          <NavbarItem className="hidden sm:flex gap-2">
            <Link isExternal href={appSiteConfig.links.github} aria-label="Github">
              <GithubIcon className="text-[#d9d4c7] hover:text-[#f6d27c] transition-colors" />
            </Link>
            {/* <ThemeSwitch /> */}
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
              <RouterLink to={'/login'}>
                <button className="gm-primary-btn rounded-full px-5 h-10 text-sm">{t('Sign in')}</button>
              </RouterLink>
            )}
          </NavbarItem>
        </NavbarContent>
        <NavbarContent className="sm:hidden basis-1 pl-4" justify="end">
          <Link isExternal href={appSiteConfig.links.github} aria-label="Github">
            <GithubIcon className="text-default-500" />
          </Link>
          {/* <ThemeSwitch /> */}
          <NavbarMenuToggle />
        </NavbarContent>
        <NavbarMenu>
          <div className="mx-4 mt-2 flex flex-col gap-2">
            {appSiteConfig.navMenuItems.map((item, index) => (
              <NavbarMenuItem key={`${item}-${index}`}>
                <Link
                  color={
                    index === 2
                      ? 'primary'
                      : index === appSiteConfig.navMenuItems.length - 1
                        ? 'danger'
                        : 'foreground'
                  }
                  href="#"
                  size="lg"
                >
                  {t(item.label)}
                </Link>
              </NavbarMenuItem>
            ))}
          </div>
        </NavbarMenu>
      </NextUINavbar>
      <Modal
        backdrop="opaque"
        isOpen={isOpen}
        onOpenChange={onOpenChange}
        classNames={{
          backdrop: 'gm-overlay-backdrop',
          base: 'gm-overlay-surface',
          header: 'text-[var(--gm-text-main)]',
          body: 'text-[var(--gm-text-main)]',
          closeButton: 'text-[var(--gm-text-muted)] hover:bg-white/10',
        }}
      >
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1">
                {t("Complete your team's onboarding")}
              </ModalHeader>
              <ModalBody>
                <div className="mx-auto w-full flex items-center justify-center rounded-full">
                  <GithubIcon size={50} />
                  <div className="h-1 w-1 rounded-full bg-[var(--gm-accent)] animate-pulse mx-3 ml-5"></div>
                  <div className="h-1 w-1 rounded-full bg-[var(--gm-accent)] animate-pulse mx-3 mr-5"></div>
                  <Logo size={60} />
                  <div className="h-1 w-1 rounded-full bg-[var(--gm-accent)] animate-pulse mx-3 ml-5"></div>
                  <div className="h-1 w-1 rounded-full bg-[var(--gm-accent)] animate-pulse mx-3 mr-5"></div>
                  <LarkWhiteIcon size={50} />
                </div>
                {!account?.current_team ? (
                  <p className="text-sm text-[var(--gm-text-muted)] text-center">
                    {t('Add your code repository')} {t('GitMaya connects to GitHub.')}
                  </p>
                ) : (
                  <p className="text-sm text-[var(--gm-text-muted)] text-center">
                    {t('Add your Lark workspace')} {t('Enable developer feedback and PR - Channels.')}
                  </p>
                )}

                <Button color="danger" onPress={onboarding}>
                  {t('Continue onboarding')}
                </Button>
                <Button color="danger" variant="light" onPress={onClose}>
                  {t('Cancel')}
                </Button>
              </ModalBody>
            </>
          )}
        </ModalContent>
      </Modal>
    </>
  );
};
