import React, { useState, useEffect } from 'react';

const TypingAnimation = ({ text, speed = 20, onComplete }) => {
    const [displayedText, setDisplayedText] = useState('');
    const [isTyping, setIsTyping] = useState(true);

    useEffect(() => {
        setDisplayedText(''); // Reset on text change
        let i = 0;
        const typingInterval = setInterval(() => {
            if (i < text.length) {
                setDisplayedText(prev => prev + text.charAt(i));
                i++;
            } else {
                clearInterval(typingInterval);
                setIsTyping(false);
                if (onComplete) onComplete();
            }
        }, speed);

        return () => clearInterval(typingInterval);
    }, [text, speed, onComplete]);

    return <p>{displayedText}{isTyping && <span className="typing-cursor"></span>}</p>;
};

export default TypingAnimation;