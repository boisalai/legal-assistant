"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { authApi } from "@/lib/api";
import {
  FolderOpen,
  MessageSquare,
  FileSearch,
  Settings,
  LogOut,
  HelpCircle,
  User,
  ChevronUp,
  Scale,
  ShieldCheck,
  Database,
  KeyRound,
  Users,
  Wrench,
  FileText,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useState, useEffect } from "react";

interface NavItem {
  titleKey: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const mainNavItems: NavItem[] = [
  {
    titleKey: "nav.courses",
    href: "/courses",
    icon: FolderOpen,
  },
  {
    titleKey: "nav.assistant",
    href: "/assistant",
    icon: MessageSquare,
  },
  {
    titleKey: "nav.analysis",
    href: "/analysis",
    icon: FileSearch,
  },
];

export function AppSidebar() {
  const t = useTranslations();
  const pathname = usePathname();
  const router = useRouter();
  const [userName, setUserName] = useState("User");
  const [userEmail, setUserEmail] = useState("user@example.com");
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    const fetchUserInfo = async () => {
      try {
        const user = await authApi.getCurrentUser();
        setUserName(`${user.prenom} ${user.nom}`.trim() || "User");
        setUserEmail(user.email || "user@example.com");
        setIsAdmin(user.role === "admin");
      } catch {
        // Token was invalid or expired - this is expected behavior
        // The token has been cleared by fetchApi, just keep default values
      }
    };
    if (authApi.isAuthenticated()) {
      fetchUserInfo();
    }
  }, []);

  const handleLogout = () => {
    authApi.logout();
    router.push("/login");
  };

  const getUserInitials = (name: string): string => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <Sidebar>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/courses">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
                  <Scale className="size-4" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">{t("common.appName")}</span>
                  <span className="truncate text-xs">Legal Assistant</span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {mainNavItems.map((item) => {
                const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
                return (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton asChild isActive={isActive}>
                      <Link href={item.href}>
                        <item.icon className="h-4 w-4" />
                        <span>{t(item.titleKey)}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Admin Section - Only visible for admins */}
        {isAdmin && (
          <SidebarGroup>
            <SidebarGroupLabel>Administration</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton asChild isActive={pathname === "/admin/users"}>
                    <Link href="/admin/users">
                      <Users className="h-4 w-4" />
                      <span>Utilisateurs</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton asChild isActive={pathname === "/admin/database"}>
                    <Link href="/admin/database">
                      <Database className="h-4 w-4" />
                      <span>Base de données</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton asChild isActive={pathname === "/admin/passwords"}>
                    <Link href="/admin/passwords">
                      <KeyRound className="h-4 w-4" />
                      <span>Mots de passe</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {/* Tools Section */}
        <SidebarGroup>
          <SidebarGroupLabel>{t("nav.tools")}</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild isActive={pathname === "/tools/markdown-converter"}>
                  <Link href="/tools/markdown-converter">
                    <FileText className="h-4 w-4" />
                    <span>{t("nav.markdownConverter")}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        {/* User Menu */}
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton size="lg" className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground">
                  <Avatar className="h-8 w-8 rounded-lg">
                    <AvatarImage src="" alt={userName} />
                    <AvatarFallback className="rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 text-white font-semibold">
                      {getUserInitials(userName)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="grid flex-1 text-left text-sm leading-tight">
                    <span className="truncate font-semibold">{userName}</span>
                    <span className="truncate text-xs">{userEmail}</span>
                  </div>
                  <ChevronUp className="ml-auto size-4" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg"
                side="top"
                align="end"
                sideOffset={4}
              >
                <DropdownMenuLabel className="p-0 font-normal">
                  <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
                    <Avatar className="h-8 w-8 rounded-lg">
                      <AvatarImage src="" alt={userName} />
                      <AvatarFallback className="rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 text-white font-semibold">
                        {getUserInitials(userName)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="grid flex-1 text-left text-sm leading-tight">
                      <span className="truncate font-semibold">{userName}</span>
                      <span className="truncate text-xs text-muted-foreground">{userEmail}</span>
                    </div>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => router.push("/settings")}>
                  <User className="mr-2 h-4 w-4" />
                  Account
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => router.push("/settings")}>
                  <Settings className="mr-2 h-4 w-4" />
                  Settings
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => window.open("https://docs.example.com", "_blank")}>
                  <HelpCircle className="mr-2 h-4 w-4" />
                  Get Help
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
