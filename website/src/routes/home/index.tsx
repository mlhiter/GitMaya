import { Cobe, Actions } from './components';

const Home = () => {
  return (
    <div className="bg-dark pb-16 sm:pb-24">
      <section className="px-4 sm:px-8 pt-4 sm:pt-8">
        <div className="mx-auto w-full max-w-7xl gm-fade-up">
          <Cobe />
        </div>
      </section>
      <section className="mx-auto w-full max-w-5xl px-4 sm:px-8 mt-6 sm:mt-8 gm-fade-up-delay">
        <Actions />
      </section>
    </div>
  );
};

export default Home;
