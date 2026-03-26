export type AppSiteConfig = typeof appSiteConfig;

export const appSiteConfig = {
  navItems: [
    {
      label: 'People',
      href: '/app/people',
    },
    {
      label: 'Repo',
      href: '/app/repo',
    },
  ],
  navMenuItems: [
    {
      label: 'People',
      href: '/app/people',
    },
    {
      label: 'Repo',
      href: '/app/repo',
    },
    {
      label: 'Logout',
      href: '/logout',
    },
  ],
  links: {
    github: 'https://github.com/mlhiter/GitMaya',
    twitter: 'https://github.com/mlhiter/GitMaya',
    docs: 'https://github.com/mlhiter/GitMaya',
    discord: 'https://github.com/mlhiter/GitMaya',
    sponsor: 'https://github.com/mlhiter/GitMaya',
  },
};
