import { Logo } from '@/components/icons';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export const Footer = ({ className }: { className?: string }) => {
  const { t } = useTranslation();

  return (
    <footer className={className}>
      <div className="w-full border-t border-white/10">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-5 px-4 py-7 sm:px-6">
          <Link to="/" className="flex items-center gap-3">
            <Logo height={30} width={30} />
            <div className="gm-brand text-lg font-bold text-[#f2e8cf]">GitMaya</div>
          </Link>

          <div className="text-sm text-[var(--gm-text-muted)]">
            © GitMaya. {t('All rights reserved.')}
          </div>
        </div>
      </div>
    </footer>
  );
};
