"use client";

import { useState } from "react";
import Sidebar from "@/components/common/sidebar";
import UserProfileMenu from "@/components/common/UserProfileMenu";
import Header from "@/components/common/Header"; // [Fix] Import restored

interface PageLayoutProps {
    children: React.ReactNode;
    subTitle?: string;
    isTransparent?: boolean;
    headerTheme?: "light" | "dark";
    className?: string; // Wrapper className
    mainClassName?: string; // Main className passed to children wrapper if needed, or consumers handle it
    sidebarContext?: "home" | "chat"; // [NEW] Context for Sidebar
    disableContentPadding?: boolean; // [NEW] Disable default padding for full-screen apps like Chat
}

export default function PageLayout({
    children,
    subTitle,
    isTransparent = false,
    headerTheme = "light",
    className = "min-h-screen bg-[#FDFBF8] text-[#2B2B2B] font-sans",
    sidebarContext = "home", // Default to home
    disableContentPadding = false, // Default to false (standard padding enabled)
}: PageLayoutProps) {
    const [isNavOpen, setIsNavOpen] = useState(false);
    const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);

    return (
        <div className={`${className}`}>
            <Sidebar
                isOpen={isNavOpen}
                onClose={() => setIsNavOpen(false)}
                context={sidebarContext}
            />
            {/* Profile Menu is now a sibling, free from Header's stacking context */}
            <UserProfileMenu
                isOpen={isProfileMenuOpen}
                onClose={() => setIsProfileMenuOpen(false)}
            />

            {isNavOpen && (
                <div
                    className="fixed inset-0 bg-transparent z-40"
                    onClick={() => setIsNavOpen(false)}
                />
            )}

            <Header
                onToggleSidebar={() => {
                    if (!isNavOpen) setIsProfileMenuOpen(false); // Close profile if opening sidebar
                    setIsNavOpen(!isNavOpen);
                }}
                isSidebarOpen={isNavOpen}
                onToggleProfile={() => {
                    if (!isProfileMenuOpen) setIsNavOpen(false); // Close sidebar if opening profile
                    setIsProfileMenuOpen(!isProfileMenuOpen);
                }}
                isProfileMenuOpen={isProfileMenuOpen} // Pass state
                subTitle={subTitle}
                isTransparent={isTransparent}
                theme={headerTheme}
            />

            {disableContentPadding ? (
                children
            ) : (
                <div className="max-w-5xl mx-auto px-4 sm:px-6 pt-[96px] sm:pt-[120px] pb-12">
                    {children}
                </div>
            )}

        </div>
    );
}
