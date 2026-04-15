import { Footer } from '@/layout/footer';
import { StepGuide, GithubInstallation, WorkSpaceInstallation } from './components';
import { useEffect, useState } from 'react';
import { HeaderContent } from '@/layout/app';
import { useTeamInfoStore } from '@/stores';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

type StepComponentType = React.FC<{
  step: number;
  setStep: React.Dispatch<React.SetStateAction<number>>;
}>;

const stepComponents: Record<number, StepComponentType> = {
  0: GithubInstallation,
  1: WorkSpaceInstallation,
};

const Induction = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const teamInfo = useTeamInfoStore.use.teamInfo();
  const [step, setStep] = useState(0);
  const StepComponent = stepComponents[step];

  useEffect(() => {
    if (teamInfo?.code_application && teamInfo?.im_application) {
      navigate('/app/people', { replace: true });
      return;
    }
    if (teamInfo?.code_application && !teamInfo.im_application) {
      setStep(1);
      return;
    }
    setStep(0);
  }, [navigate, teamInfo?.code_application, teamInfo?.im_application]);

  return (
    <div className="flex-grow flex flex-col">
      <div>
        <HeaderContent title={t(`stepHeaders.${step}.title`)}>
          <p className="text-md text-[var(--gm-text-muted)] max-w-7xl px-4 sm:px-6 lg:px-8 mx-auto mt-6">
            {t(`stepHeaders.${step}.content1`)}
          </p>
          <p className="text-md text-[var(--gm-text-muted)] max-w-7xl px-4 sm:px-6 lg:px-8 mx-auto mt-6">
            {t(`stepHeaders.${step}.content2`)}
          </p>
        </HeaderContent>
      </div>
      <main className="gm-panel container max-w-7xl mx-auto px-4 sm:px-6 flex-grow rounded-3xl py-4 sm:py-6">
        <div className="grow flex max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <StepGuide step={step} setStep={setStep} />
          <div className="grow p-8">{<StepComponent step={step} setStep={setStep} />}</div>
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default Induction;
