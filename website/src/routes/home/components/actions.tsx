import { GithubIcon } from '@/components/icons';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export const Actions: React.FC = () => {
  const { t } = useTranslation();

  return (
    <div className="gm-panel rounded-3xl px-6 py-8 text-left sm:px-10 sm:py-10">
      <div className="mb-5 inline-flex gm-chip rounded-full px-3 py-1 text-xs font-semibold tracking-[0.06em] uppercase">
        GitOps In Chat
      </div>

      <div className="grid gap-7 md:grid-cols-[1.3fr_1fr] md:items-end">
        <div>
          <h2 className="gm-brand text-3xl font-bold leading-tight text-[#f2e8cf] sm:text-4xl">
            One chat.
            <br />
            One repo.
          </h2>
          <p className="mt-4 max-w-xl text-sm leading-relaxed text-[var(--gm-text-muted)] sm:text-base">
            {t('Make Git Flow In Chat')}. {t('Sign in with your team\'s repository')}.{' '}
            {t('Configuration needed!')}
          </p>
        </div>

        <div className="flex flex-col items-start gap-3 md:items-end">
          <Link
            to="/login"
            className="gm-primary-btn inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm"
          >
            <GithubIcon className="h-4 w-4" />
            {t('Try with your github')}
          </Link>
          <a
            href="https://gitmaya-doc.netlify.app/"
            className="gm-secondary-btn inline-flex items-center rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.08em]"
            target="_blank"
            rel="noreferrer"
          >
            {t('Learn more details')}
          </a>
        </div>
      </div>
    </div>
  );
};
