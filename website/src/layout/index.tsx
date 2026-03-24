import { Outlet } from 'react-router-dom';
import { Footer } from '@/layout/footer';
import { Navbar } from '@/layout/narbar';

const Layout = () => {
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
