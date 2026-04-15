import { Hero } from '@/layout/app';
import { Footer } from '@/layout/footer';
import {
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  User,
  Spinner,
  Pagination,
  Autocomplete,
  AutocompleteItem,
} from '@nextui-org/react';
import { useCallback, useState, useEffect, useMemo } from 'react';
import {
  getPlatformMember,
  getTeamMember,
  bindTeamMember,
  refreshGithubMembers,
  updatePlatformUser,
  getTaskStatus,
} from '@/api';
import useSwr from 'swr';
import useSWRMutation from 'swr/mutation';
import { useAccountStore } from '@/stores';
import { RefreshIcon } from '@/components/icons';
import { motion, useAnimation } from 'framer-motion';
import clsx from 'clsx';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';

const People = () => {
  const { t } = useTranslation();
  const githubControls = useAnimation();
  const larkControls = useAnimation();
  const [page, setPage] = useState(1);
  const [githubTaskId, setGithubTaskId] = useState<string>('');
  const [larkTaskId, setLarkTaskId] = useState<string>('');
  const [githubRefreshInterval, setGithubRefreshInterval] = useState(0);
  const [larkRefreshInterval, setLarkRefreshInterval] = useState(0);
  const account = useAccountStore.use.account();

  const team_id = account?.current_team as string;
  const size = 20;

  const columns = [
    {
      name: t('GitHub handle'),
      uid: 'github',
    },
    {
      name: t('Lark handle'),
      uid: 'lark',
    },
    { name: t('Role'), uid: 'role' },
  ];

  const { trigger } = useSWRMutation(
    `api/team/${team_id}/member`,
    (
      _url,
      {
        arg,
      }: {
        arg: {
          code_user_id: string;
          im_user_id: string;
        };
      },
    ) => bindTeamMember(team_id, arg),
  );

  const { trigger: triggerLarkUser } = useSWRMutation(`api/team/${team_id}/lark/user`, () =>
    updatePlatformUser(team_id, 'lark'),
  );

  const { trigger: triggerGithubMemberSync } = useSWRMutation(
    `api/team/${team_id}/member/refresh`,
    () => refreshGithubMembers(team_id),
  );

  const { data, mutate } = useSwr(
    team_id ? `/api/team/${team_id}/member?page=${page}&size=${size}` : null,
    () => getTeamMember(team_id, { page, size }),
  );

  const { data: githubTaskStatusData } = useSwr(
    team_id && githubTaskId ? `/api/team/${team_id}/task/${githubTaskId}` : null,
    () => getTaskStatus(team_id, githubTaskId),
    {
      refreshInterval: githubRefreshInterval,
    },
  );

  const { data: larkTaskStatusData } = useSwr(
    team_id && larkTaskId ? `/api/team/${team_id}/task/${larkTaskId}` : null,
    () => getTaskStatus(team_id, larkTaskId),
    {
      refreshInterval: larkRefreshInterval,
    },
  );

  const githubTaskStatus = githubTaskStatusData?.data?.status;
  const larkTaskStatus = larkTaskStatusData?.data?.status;

  const {
    data: larkUserData,
    isLoading,
    mutate: mutateLark,
  } = useSwr(team_id ? `/api/team/${team_id}/lark/user` : null, () =>
    getPlatformMember<Lark.User[]>(team_id, 'lark'),
  );

  const larkUsers = useMemo(() => larkUserData?.data, [larkUserData]);
  const teamMember = useMemo(() => data?.data || [], [data]);
  const total = useMemo(() => {
    return data?.total ? Math.ceil(data.total / size) : 0;
  }, [data?.total, size]);

  const bindMember = useCallback(
    async (value: string, user: Github.TeamMember) => {
      try {
        await trigger({
          code_user_id: user.code_user.id,
          im_user_id: value,
        });
        mutate();
      } catch (error) {
        console.error(error);
      }
    },
    [mutate, trigger],
  );

  const renderCell = useCallback(
    (user: Github.TeamMember, columnKey: string) => {
      switch (columnKey) {
        case 'github':
          return (
            <User
              name={user.code_user.name}
              avatarProps={{ radius: 'lg', src: user.code_user.avatar }}
              description={user.code_user.email}
            >
              {user.code_user.email}
            </User>
          );
        case 'lark':
          return (
            <Autocomplete
              label="Select a user"
              className="max-w-xs"
              size="sm"
              defaultItems={larkUsers}
              classNames={{
                base: 'text-[var(--gm-text-main)]',
                selectorButton: 'text-[var(--gm-text-muted)]',
                clearButton: 'text-[var(--gm-text-muted)]',
                listboxWrapper: 'gm-overlay-list',
                listbox: 'gm-overlay-list',
                popoverContent: 'gm-overlay-surface p-1',
              }}
              onSelectionChange={(value) => bindMember(value as string, user)}
              defaultSelectedKey={user.im_user?.id}
            >
              {(user) => (
                <AutocompleteItem key={user.value} value={user.value} className="gm-overlay-item">
                  {user.label}
                </AutocompleteItem>
              )}
            </Autocomplete>
          );

        default:
          return null;
      }
    },
    [bindMember, larkUsers],
  );

  const refreshUser = useCallback(async () => {
    mutate();
    mutateLark();
  }, [mutate, mutateLark]);

  const refreshGithubUserTask = useCallback(async () => {
    const { data } = await triggerGithubMemberSync();
    if (!data?.task_id) {
      toast.error('Failed to start GitHub sync task');
      return;
    }
    setGithubTaskId(data.task_id);
  }, [triggerGithubMemberSync]);

  const refreshLarkUserTask = useCallback(async () => {
    const { data } = await triggerLarkUser();
    if (!data?.task_id) {
      toast.error('Failed to start Lark sync task');
      return;
    }
    setLarkTaskId(data.task_id);
  }, [triggerLarkUser]);

  useEffect(() => {
    setPage(1);
  }, [team_id]);

  useEffect(() => {
    if (githubTaskStatus === 'PENDING') {
      githubControls.start({
        rotate: 360,
        transition: { duration: 2, repeat: Infinity },
      });
      setGithubRefreshInterval(1000);
      return;
    }

    githubControls.stop();
    setGithubRefreshInterval(0);

    if (githubTaskStatus === 'SUCCESS') {
      setGithubTaskId('');
      mutate();
      toast.success('GitHub members refreshed!');
    } else if (githubTaskStatus === 'FAILURE') {
      setGithubTaskId('');
      toast.error('GitHub members sync failed');
    }
  }, [githubControls, githubTaskStatus, mutate]);

  useEffect(() => {
    if (larkTaskStatus === 'PENDING') {
      larkControls.start({
        rotate: 360,
        transition: { duration: 2, repeat: Infinity },
      });
      setLarkRefreshInterval(1000);
      return;
    }

    larkControls.stop();
    setLarkRefreshInterval(0);

    if (larkTaskStatus === 'SUCCESS') {
      setLarkTaskId('');
      refreshUser();
      toast.success('Lark users refreshed!');
    } else if (larkTaskStatus === 'FAILURE') {
      setLarkTaskId('');
      toast.error('Lark users sync failed');
    }
  }, [larkControls, larkTaskStatus, refreshUser]);

  return (
    <div className="flex-grow flex flex-col">
      <div className="flex-grow flex flex-col">
        <Hero>
          <div className="flex justify-between items-center mb-5">
            <h1 className="gm-brand text-3xl font-bold text-[#f2e8cf] mr-5">{t('My organization')}</h1>
          </div>
          <div
            className="gm-panel flex items-center p-4 mb-4 text-sm text-[var(--gm-text-muted)] rounded-2xl"
            role="alert"
          >
            <svg
              className="flex-shrink-0 inline w-4 h-4 me-3"
              aria-hidden="true"
              xmlns="http://www.w3.org/2000/svg"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path d="M10 .5a9.5 9.5 0 1 0 9.5 9.5A9.51 9.51 0 0 0 10 .5ZM9.5 4a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3ZM12 15H8a1 1 0 0 1 0-2h1v-3H8a1 1 0 0 1 0-2h2a1 1 0 0 1 1 1v4h1a1 1 0 0 1 0 2Z" />
            </svg>
            <span className="sr-only">{t('Info')}</span>
            <div>
              <span className="font-medium">{t('Configuration needed!')}</span>{' '}
              {t(
                'Please, associate the GitHub username to the respective Lark handle of each of your team members.',
              )}
            </div>
          </div>
        </Hero>
        <main className="gm-panel container -mt-24 max-w-7xl mx-auto flex-grow relative rounded-3xl p-2 sm:p-4">
          {isLoading ? (
            <Spinner label="Loading..." color="warning" className="absolute inset-0" />
          ) : (
            <Table
              bottomContent={
                total > 1 ? (
                  <div className="flex w-full justify-center">
                    <Pagination
                      isCompact
                      showControls
                      showShadow
                      color="default"
                      page={page}
                      total={total}
                      onChange={(page) => setPage(page)}
                    />
                  </div>
                ) : null
              }
            >
              <TableHeader>
                {columns.map((column) => (
                  <TableColumn key={column.uid} align="start">
                    <div className="flex items-center gap-2">
                      {column.name}
                      {column.uid === 'github' && (
                        <motion.div animate={githubControls}>
                          <RefreshIcon
                            size={18}
                            className={clsx('cursor-pointer', {
                              'cursor-not-allowed pointer-events-none': githubTaskStatus === 'PENDING',
                            })}
                            onClick={refreshGithubUserTask}
                          />
                        </motion.div>
                      )}
                      {column.uid === 'lark' && (
                        <motion.div animate={larkControls}>
                          <RefreshIcon
                            size={18}
                            className={clsx('cursor-pointer', {
                              'cursor-not-allowed pointer-events-none': larkTaskStatus === 'PENDING',
                            })}
                            onClick={refreshLarkUserTask}
                          />
                        </motion.div>
                      )}
                    </div>
                  </TableColumn>
                ))}
              </TableHeader>
              <TableBody>
                {teamMember.map((item) => (
                  <TableRow key={item.id}>
                    {(columnKey) => <TableCell>{renderCell(item, columnKey as string)}</TableCell>}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </main>
      </div>
      <Footer />
    </div>
  );
};

export default People;
