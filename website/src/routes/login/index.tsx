import { GithubIcon, Logo } from '@/components/icons';
import { Footer } from '@/layout/footer';
import { useOauthDialog } from '@/hooks';
import { useNavigate, Link } from 'react-router-dom';
import { useAccountStore } from '@/stores';
import { useTranslation } from 'react-i18next';

const Login = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const updateAccount = useAccountStore.use.updateAccount();

  const handleSignInGithub = useOauthDialog({
    url: '/api/github/oauth',
    event: 'oauth',
    callback: () => {
      navigate('/app/people');
      updateAccount();
    },
  });

  return (
    <div className="gm-shell flex min-h-screen flex-col overflow-hidden">
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -left-20 top-24 h-64 w-64 rounded-full bg-[color:color-mix(in_oklch,var(--gm-accent)_24%,transparent)] blur-3xl" />
        <div className="absolute right-0 top-[18%] h-72 w-72 rounded-full bg-[color:color-mix(in_oklch,var(--gm-accent-strong)_18%,transparent)] blur-3xl" />
      </div>

      <main className="mx-auto flex w-full max-w-6xl flex-1 items-center px-4 py-10 sm:px-6 sm:py-16">
        <section className="grid w-full gap-6 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="gm-fade-up rounded-3xl border border-white/10 bg-white/[0.02] p-7 sm:p-10">
            <div className="mb-7 flex items-center gap-3">
              <Logo />
              <div className="gm-brand text-2xl font-bold text-[#f2e8cf]">GitMaya</div>
            </div>

            <div className="inline-flex rounded-full gm-chip px-3 py-1 text-xs font-semibold uppercase tracking-[0.09em]">
              One Chat = One Repo
            </div>

            <h1 className="gm-brand mt-5 text-4xl font-bold leading-tight text-[#f2e8cf] sm:text-5xl">
              {t('Welcome to')} GitMaya
            </h1>
            <p className="mt-4 max-w-xl text-sm leading-relaxed text-[var(--gm-text-muted)] sm:text-base">
              {t("Sign in with your team's repository")}. {t('preferred')}. {t('Learn more details')}
              .
            </p>

            <div className="mt-8 grid gap-3 text-sm text-[var(--gm-text-muted)] sm:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                <div className="text-xs uppercase tracking-[0.12em] text-[var(--gm-text-main)]/70">
                  Git Provider
                </div>
                <div className="mt-1 text-[var(--gm-text-main)]">GitHub App</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                <div className="text-xs uppercase tracking-[0.12em] text-[var(--gm-text-main)]/70">
                  Runtime
                </div>
                <div className="mt-1 text-[var(--gm-text-main)]">Local Dev / Self-hosted</div>
              </div>
            </div>
          </div>

          <div className="gm-panel gm-fade-up-delay rounded-3xl p-7 sm:p-10">
            <h2 className="gm-brand text-2xl font-bold text-[#f2e8cf]">{t("let's get started!")}</h2>
            <p className="mt-3 text-sm leading-relaxed text-[var(--gm-text-muted)]">
              {t('Sign in with Github')} to continue onboarding and manage your repository-to-chat workflow.
            </p>

            <button
              onClick={handleSignInGithub}
              type="button"
              className="gm-primary-btn mt-8 inline-flex h-12 w-full items-center justify-center gap-2 rounded-full px-5 text-sm sm:text-base"
            >
              <GithubIcon className="size-5" />
              {t('Sign in with Github')}
            </button>

            <div className="mt-5 text-xs leading-relaxed text-[var(--gm-text-muted)]">
              OAuth callback and session will be kept on the same host. For local dev, keep both web and API
              on <code className="rounded bg-white/10 px-1 py-0.5 text-[11px]">127.0.0.1</code>.
            </div>

            <div className="mt-7 flex items-center justify-between border-t border-white/10 pt-5 text-xs text-[var(--gm-text-muted)]">
              <span>{t('preferred')}</span>
              <Link className="underline-offset-4 hover:underline" to="/">
                Back Home
              </Link>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
};

export default Login;
