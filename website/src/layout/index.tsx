import { Outlet } from 'react-router-dom';
import { Footer } from '@/layout/footer';
import { Navbar } from '@/layout/narbar';
import { useEffect } from 'react';
import { useAccountStore } from '@/stores';

const Layout = () => {
  const hydrateAccount = useAccountStore.use.hydrateAccount();

  useEffect(() => {
    void hydrateAccount().catch(() => undefined);
  }, [hydrateAccount]);

  return (
    <div className="gm-shell relative flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-grow w-full">
        <Outlet />
      </main>
      <Footer className="bg-transparent" />
    </div>
  );
};

export default Layout;
