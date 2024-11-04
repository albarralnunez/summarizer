import React from 'react';

interface ThemeSwitchProps {
  isDarkMode: boolean;
  toggleTheme: () => void;
}

export const ThemeSwitch: React.FC<ThemeSwitchProps> = ({ isDarkMode, toggleTheme }) => {
  return (
    <button onClick={toggleTheme} className="theme-toggle">
      {isDarkMode ? '☀️' : '🌙'}
    </button>
  );
};
