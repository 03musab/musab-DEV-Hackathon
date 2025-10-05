import React, { useEffect, useState } from 'react';
import { CheckCircle, XCircle, Info, X } from 'lucide-react';

const toastTypes = {
    success: {
        icon: <CheckCircle size={20} />,
        className: 'toast-success',
    },
    error: {
        icon: <XCircle size={20} />,
        className: 'toast-error',
    },
    info: {
        icon: <Info size={20} />,
        className: 'toast-info',
    },
};

const Toast = ({ toast, removeToast }) => {
    const { id, message, type } = toast;
    const { icon, className } = toastTypes[type] || toastTypes.info;
    const [isExiting, setIsExiting] = useState(false);

    useEffect(() => {
        const timer = setTimeout(() => {
            setIsExiting(true);
            setTimeout(() => removeToast(id), 400); // Wait for animation
        }, 5000);

        return () => clearTimeout(timer);
    }, [id, removeToast]);

    return (
        <div className={`toast ${className} ${isExiting ? 'exit' : ''}`}>
            <div className="toast-icon">{icon}</div>
            <p className="toast-message">{message}</p>
        </div>
    );
};

export default Toast;