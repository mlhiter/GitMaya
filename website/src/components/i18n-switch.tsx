import { Tooltip, Button } from '@nextui-org/react';
import { I18nIcon } from '@/components/icons';
import i18n from '@/i18n';

export const I18nSwitch = () => {
  const onAction = (key: string | number) => {
    i18n.changeLanguage(key as string);
  };
  return (
    <div className="flex items-center gap-4">
      <Tooltip
        delay={100}
        content={
          <div className="gm-overlay-surface flex min-w-32 flex-col rounded-xl p-1">
            <Button
              color="default"
              variant="light"
              className="justify-start text-[var(--gm-text-main)] hover:bg-[var(--gm-overlay-hover)]"
              onClick={() => onAction('en-US')}
            >
              English
            </Button>
            <Button
              color="default"
              variant="light"
              className="justify-start text-[var(--gm-text-main)] hover:bg-[var(--gm-overlay-hover)]"
              onClick={() => onAction('zh-CN')}
            >
              简体中文
            </Button>
            <Button
              color="default"
              variant="light"
              className="justify-start text-[var(--gm-text-main)] hover:bg-[var(--gm-overlay-hover)]"
              onClick={() => onAction('vi-VN')}
            >
              Tiếng
            </Button>
          </div>
        }
        placement="bottom"
        className="p-0 bg-transparent"
        classNames={{
          content: 'bg-transparent p-0 shadow-none',
        }}
      >
        <span className="cursor-pointer">
          <I18nIcon className="text-default-500" />
        </span>
      </Tooltip>
    </div>
  );
};
