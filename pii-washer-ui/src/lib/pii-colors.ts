import type { PIICategory } from '@/types/api';

export interface CategoryColor {
  highlightBg: string;
  highlightBgActive: string;
  badgeBg: string;
  badgeText: string;
  label: string;
}

export const PII_COLORS: Record<PIICategory, CategoryColor> = {
  NAME: {
    highlightBg: 'rgba(80, 135, 230, 0.18)',
    highlightBgActive: 'rgba(80, 135, 230, 0.35)',
    badgeBg: 'rgb(80, 135, 230)',
    badgeText: 'white',
    label: 'Name',
  },
  ADDRESS: {
    highlightBg: 'rgba(65, 185, 110, 0.18)',
    highlightBgActive: 'rgba(65, 185, 110, 0.35)',
    badgeBg: 'rgb(65, 185, 110)',
    badgeText: 'white',
    label: 'Address',
  },
  PHONE: {
    highlightBg: 'rgba(155, 110, 225, 0.18)',
    highlightBgActive: 'rgba(155, 110, 225, 0.35)',
    badgeBg: 'rgb(155, 110, 225)',
    badgeText: 'white',
    label: 'Phone',
  },
  EMAIL: {
    highlightBg: 'rgba(220, 130, 55, 0.18)',
    highlightBgActive: 'rgba(220, 130, 55, 0.35)',
    badgeBg: 'rgb(220, 130, 55)',
    badgeText: 'white',
    label: 'Email',
  },
  SSN: {
    highlightBg: 'rgba(215, 85, 85, 0.18)',
    highlightBgActive: 'rgba(215, 85, 85, 0.35)',
    badgeBg: 'rgb(215, 85, 85)',
    badgeText: 'white',
    label: 'SSN',
  },
  DOB: {
    highlightBg: 'rgba(55, 180, 165, 0.18)',
    highlightBgActive: 'rgba(55, 180, 165, 0.35)',
    badgeBg: 'rgb(55, 180, 165)',
    badgeText: 'white',
    label: 'Date of Birth',
  },
  CCN: {
    highlightBg: 'rgba(210, 95, 155, 0.18)',
    highlightBgActive: 'rgba(210, 95, 155, 0.35)',
    badgeBg: 'rgb(210, 95, 155)',
    badgeText: 'white',
    label: 'Credit Card',
  },
  IP: {
    highlightBg: 'rgba(210, 175, 45, 0.18)',
    highlightBgActive: 'rgba(210, 175, 45, 0.35)',
    badgeBg: 'rgb(210, 175, 45)',
    badgeText: 'black',
    label: 'IP Address',
  },
  URL: {
    highlightBg: 'rgba(110, 115, 220, 0.18)',
    highlightBgActive: 'rgba(110, 115, 220, 0.35)',
    badgeBg: 'rgb(110, 115, 220)',
    badgeText: 'white',
    label: 'URL',
  },
};
