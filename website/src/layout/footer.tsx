import { useLocalStorageState } from 'ahooks';
import clsx from 'clsx';
import { Logo, LarkWhiteIcon } from '@/components/icons';
import { Link } from 'react-router-dom';
import LarkQR from '@/assets/lark-group-QR.jpg';
import { Tooltip, Image } from '@nextui-org/react';
import { useTranslation } from 'react-i18next';

export const Footer = ({ className }: { className?: string }) => {
  const { t } = useTranslation();
  const [showCookie, setShowCookie] = useLocalStorageState('showCookie', {
    serializer: JSON.stringify,
    deserializer: JSON.parse,
    defaultValue: true,
  });

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

          <div className="ml-auto flex items-center gap-4">
            <Tooltip
              content={<Image src={LarkQR} width={260} />}
              placement="top"
              className="p-0 bg-transparent"
            >
              <button
                type="button"
                className="flex h-9 w-9 items-center justify-center rounded-full border border-white/20 bg-white/5 text-[#f2e8cf] transition hover:border-[var(--gm-accent)] hover:text-[#f6d27c]"
                aria-label="Lark group"
              >
                <LarkWhiteIcon />
              </button>
            </Tooltip>
          </div>
        </div>
      </div>

      <div
        className={clsx(
          'fixed bottom-5 left-1/2 z-40 w-[min(92vw,880px)] -translate-x-1/2 rounded-2xl p-4 shadow-2xl md:p-5',
          'gm-panel',
          showCookie ? 'block' : 'hidden',
        )}
      >
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between md:gap-6">
          <p className="text-sm leading-relaxed text-[var(--gm-text-muted)]">
            {t('We use cookies in this website to give you the best experience on our site.')}
          </p>
          <button
            onClick={() => setShowCookie(false)}
            className="gm-primary-btn h-10 rounded-full px-5 text-sm"
          >
            Okay
          </button>
        </div>
      </div>
    </footer>
  );
};
