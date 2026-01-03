"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  RefreshCw,
  Copy,
  Check,
  KeyRound,
  Settings2,
  Loader2,
  AlertCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { adminApi, authApi, PasswordGenerateResponse } from "@/lib/api";
import { AppShell } from "@/components/layout/app-shell";

export default function AdminPasswordsPage() {
  const router = useRouter();

  // State
  const [passwords, setPasswords] = useState<PasswordGenerateResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Generation options
  const [count, setCount] = useState(20);
  const [length, setLength] = useState(16);
  const [includeUppercase, setIncludeUppercase] = useState(true);
  const [includeLowercase, setIncludeLowercase] = useState(true);
  const [includeDigits, setIncludeDigits] = useState(true);
  const [includeSymbols, setIncludeSymbols] = useState(true);
  const [excludeAmbiguous, setExcludeAmbiguous] = useState(false);

  // Check if user is admin on mount
  useEffect(() => {
    const checkAuth = async () => {
      if (!authApi.isAuthenticated()) {
        router.push("/login");
        return;
      }

      try {
        const user = await authApi.getCurrentUser();
        if (user.role !== "admin") {
          router.push("/courses");
          return;
        }
        // Auto-generate on mount
        await generatePasswords();
      } catch {
        router.push("/login");
      }
    };

    checkAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  const generatePasswords = async () => {
    setLoading(true);
    setError(null);

    try {
      const results = await adminApi.passwords.generate({
        count,
        length,
        includeUppercase,
        includeLowercase,
        includeDigits,
        includeSymbols,
        excludeAmbiguous,
      });
      setPasswords(results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la génération");
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async (password: string, index: number) => {
    try {
      await navigator.clipboard.writeText(password);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch {
      // Clipboard API not available
    }
  };

  const getStrengthBadge = (strength: string, score: number) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      "Très fort": "default",
      "Fort": "secondary",
      "Moyen": "outline",
      "Faible": "destructive",
    };

    return (
      <Badge variant={variants[strength] || "outline"}>
        {strength} ({score}/100)
      </Badge>
    );
  };

  return (
    <AppShell noPadding>
      <div className="flex flex-col h-full overflow-hidden">
        {/* Header - fixed 65px */}
        <div className="px-4 border-b bg-background flex items-center justify-between shrink-0 h-[65px]">
          <h2 className="text-xl font-bold">Générateur de mots de passe</h2>
        </div>

        {/* Scrollable content */}
        <div className="px-6 py-2 space-y-4 flex-1 min-h-0 overflow-y-auto">
          {/* Error display */}
          {error && (
            <div className="flex items-center gap-2 p-3 border border-destructive rounded-md text-destructive text-sm">
              <AlertCircle className="h-4 w-4" />
              <span>{error}</span>
            </div>
          )}

          {/* Options section - collapsible */}
          <div className="space-y-2">
            <Collapsible open={settingsOpen} onOpenChange={setSettingsOpen}>
              <div className="flex items-center justify-between">
                <CollapsibleTrigger asChild>
                  <button className="font-semibold text-base flex items-center gap-2 hover:text-primary transition-colors">
                    <Settings2 className="h-4 w-4" />
                    Options de génération
                  </button>
                </CollapsibleTrigger>
                <Button variant="ghost" size="sm" onClick={() => setSettingsOpen(!settingsOpen)}>
                  {settingsOpen ? "Masquer" : "Afficher"}
                </Button>
              </div>
              <CollapsibleContent>
                <div className="mt-3 p-4 border rounded-md space-y-4">
                  {/* Length slider */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label className="text-sm">Longueur</Label>
                      <span className="text-sm font-medium">{length} caractères</span>
                    </div>
                    <Slider
                      value={[length]}
                      onValueChange={(v) => setLength(v[0])}
                      min={8}
                      max={64}
                      step={1}
                      className="w-full"
                    />
                  </div>

                  {/* Count input */}
                  <div className="space-y-1">
                    <Label htmlFor="count" className="text-sm">Nombre de mots de passe</Label>
                    <Input
                      id="count"
                      type="number"
                      value={count}
                      onChange={(e) => setCount(Math.max(1, Math.min(100, parseInt(e.target.value) || 20)))}
                      min={1}
                      max={100}
                      className="w-32 h-8 text-sm"
                    />
                  </div>

                  {/* Character options */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="uppercase" className="text-sm">Majuscules (A-Z)</Label>
                      <Switch
                        id="uppercase"
                        checked={includeUppercase}
                        onCheckedChange={setIncludeUppercase}
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <Label htmlFor="lowercase" className="text-sm">Minuscules (a-z)</Label>
                      <Switch
                        id="lowercase"
                        checked={includeLowercase}
                        onCheckedChange={setIncludeLowercase}
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <Label htmlFor="digits" className="text-sm">Chiffres (0-9)</Label>
                      <Switch
                        id="digits"
                        checked={includeDigits}
                        onCheckedChange={setIncludeDigits}
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <Label htmlFor="symbols" className="text-sm">Symboles (!@#$...)</Label>
                      <Switch
                        id="symbols"
                        checked={includeSymbols}
                        onCheckedChange={setIncludeSymbols}
                      />
                    </div>
                  </div>

                  {/* Ambiguous option */}
                  <div className="flex items-center justify-between border-t pt-3">
                    <div>
                      <Label htmlFor="ambiguous" className="text-sm">Exclure les caractères ambigus</Label>
                      <p className="text-xs text-muted-foreground">
                        Évite 0, O, l, 1, I qui se ressemblent
                      </p>
                    </div>
                    <Switch
                      id="ambiguous"
                      checked={excludeAmbiguous}
                      onCheckedChange={setExcludeAmbiguous}
                    />
                  </div>

                  <Button size="sm" onClick={generatePasswords} className="w-full gap-1" disabled={loading}>
                    {loading ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <RefreshCw className="h-3 w-3" />
                    )}
                    Appliquer et régénérer
                  </Button>
                </div>
              </CollapsibleContent>
            </Collapsible>
          </div>

          {/* Passwords section */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-base flex items-center gap-2">
                <KeyRound className="h-4 w-4" />
                Mots de passe générés ({passwords.length})
              </h3>
              <Button size="sm" onClick={generatePasswords} disabled={loading} className="gap-1">
                {loading ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <RefreshCw className="h-3 w-3" />
                )}
                Régénérer
              </Button>
            </div>

            {/* Passwords table */}
            <div className="border rounded-md">
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : passwords.length === 0 ? (
                <div className="flex items-center justify-center py-8">
                  <p className="text-sm text-muted-foreground">Aucun mot de passe généré</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12 text-sm">#</TableHead>
                      <TableHead className="text-sm">Mot de passe</TableHead>
                      <TableHead className="w-32 text-sm">Force</TableHead>
                      <TableHead className="w-16 text-sm">Copier</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {passwords.map((pwd, index) => (
                      <TableRow key={index}>
                        <TableCell className="text-sm text-muted-foreground">
                          {index + 1}
                        </TableCell>
                        <TableCell>
                          <code className="font-mono text-sm bg-muted px-2 py-1 rounded">
                            {pwd.password}
                          </code>
                        </TableCell>
                        <TableCell>
                          {getStrengthBadge(pwd.strength, pwd.score)}
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => copyToClipboard(pwd.password, index)}
                          >
                            {copiedIndex === index ? (
                              <Check className="h-4 w-4 text-green-500" />
                            ) : (
                              <Copy className="h-4 w-4" />
                            )}
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
