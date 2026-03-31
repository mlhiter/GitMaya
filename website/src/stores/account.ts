import { create } from 'zustand';
import { createSelectors } from './helper';
import i18n from '@/i18n';
import { getAccount } from '@/api';
import { isAxiosError } from 'axios';

interface AccountState {
  account: Github.Account | null;
  setAccount: (account: Github.Account | null) => void;
  lang: string;
  setLang: (lang: string) => void;
  updateAccount: () => Promise<void>;
  hydrateAccount: () => Promise<void>;
}

const useAccountStoreBase = create<AccountState>((set) => ({
  account: null,
  setAccount: (account) => set({ account }),
  lang: localStorage.getItem('lang') || 'en_US',
  setLang: (lang) => {
    i18n.changeLanguage(lang);
    localStorage.setItem('lang', lang);
    set({ lang });
  },
  updateAccount: async () => {
    const { data } = await getAccount();
    set({ account: data });
  },
  hydrateAccount: async () => {
    try {
      const { data } = await getAccount({ skipAuthRedirect: true });
      set({ account: data });
    } catch (error) {
      if (isAxiosError(error) && error.response?.status === 401) {
        set({ account: null });
        return;
      }
      throw error;
    }
  },
}));

export const useAccountStore = createSelectors(useAccountStoreBase);
