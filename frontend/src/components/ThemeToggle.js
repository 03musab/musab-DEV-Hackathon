import React, { useState, useEffect } from 'react';
import { Sun, Moon } from 'lucide-react';

const ThemeToggle = () => {
    // Initialize theme from localStorage or default to 'dark'
    const [theme, setTheme] = useState(() => {
        const savedTheme = localStorage.getItem('theme');
        return savedTheme || 'dark';
    });

    useEffect(() => {
        // Apply the theme to the body and save to localStorage
        document.body.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }, [theme]);

    const toggleTheme = () => {
        setTheme(prevTheme => (prevTheme === 'light' ? 'dark' : 'light'));
    };

    return (
        <div className="theme-toggle" onClick={toggleTheme} title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}>
            <div className="theme-toggle-indicator"></div>
            <button
                className={`theme-toggle-button ${theme === 'dark' ? 'active' : ''}`}
                aria-label="Switch to Dark Mode"
            >
                <Moon size={14} />
            </button>
            <button
                className={`theme-toggle-button ${theme === 'light' ? 'active' : ''}`}
                aria-label="Switch to Light Mode"
            >
                <Sun size={14} />
            </button>
        </div>
    );
};

export default ThemeToggle;