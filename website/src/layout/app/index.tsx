import { Outlet } from 'react-router-dom';
import { Navbar } from '@/layout/app/navbar';
import { useAccountStore } from '@/stores';
import { useEffect } from 'react';

const AppLayout = () => {
  const getAccount = useAccountStore.use.updateAccount();
  useEffect(() => {
    getAccount();
  }, [getAccount]);
  return (
    <div className="gm-shell relative flex min-h-screen flex-col">
      <Navbar />
      <Outlet />
    </div>
  );
};

export const HeaderContent = ({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) => (
  <header className="pt-9 pb-8">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <h1 className="gm-brand text-3xl font-bold text-[#f2e8cf]">{title}</h1>
    </div>
    <div>{children}</div>
  </header>
);

export const Hero = ({ children }: { children?: React.ReactNode }) => {
  return (
    <div className="pb-28">
      <header className="pt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">{children}</div>
      </header>
    </div>
  );
};

export default AppLayout;
