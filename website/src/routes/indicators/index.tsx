import { Hero } from '@/layout/app';
import { useTranslation } from 'react-i18next';

const Indicators = () => {
  const { t } = useTranslation();
  return (
    <div className="flex-grow flex flex-col">
      <Hero>
        <div className="flex-center">
          <h1 className="gm-brand text-3xl font-bold text-[#f2e8cf] mr-5">
            {t('Engineering indicators.')}
          </h1>
        </div>
      </Hero>
      <main className="gm-panel container -mt-24 max-w-7xl mx-auto px-4 sm:px-6 flex-grow rounded-3xl py-8">
        {t('Indicators')}
      </main>
    </div>
  );
};

export default Indicators;
