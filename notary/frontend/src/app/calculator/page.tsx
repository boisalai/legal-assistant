"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Calculator,
  DollarSign,
  Home,
  FileText,
  Calendar,
  Info,
  RotateCcw,
} from "lucide-react";

// Transfer tax brackets for Quebec (2024)
const TRANSFER_TAX_BRACKETS = [
  { min: 0, max: 58900, rate: 0.005 },
  { min: 58900, max: 294600, rate: 0.01 },
  { min: 294600, max: Infinity, rate: 0.015 },
];

// Montreal additional bracket (over $500k)
const MONTREAL_EXTRA_BRACKET = { min: 500000, max: Infinity, rate: 0.005 };

// Municipalities with higher rates
const SPECIAL_MUNICIPALITIES = [
  { name: "Montréal", hasExtraBracket: true },
  { name: "Québec", hasExtraBracket: false },
  { name: "Laval", hasExtraBracket: false },
  { name: "Gatineau", hasExtraBracket: false },
  { name: "Longueuil", hasExtraBracket: false },
  { name: "Autre", hasExtraBracket: false },
];

// Calculate transfer tax
function calculateTransferTax(
  purchasePrice: number,
  municipality: string
): { total: number; breakdown: { bracket: string; amount: number }[] } {
  const breakdown: { bracket: string; amount: number }[] = [];
  let total = 0;
  let remaining = purchasePrice;

  // Standard brackets
  for (const bracket of TRANSFER_TAX_BRACKETS) {
    if (remaining <= 0) break;

    const taxableInBracket = Math.min(
      remaining,
      bracket.max - bracket.min
    );
    const amount = taxableInBracket * bracket.rate;
    total += amount;

    if (amount > 0) {
      breakdown.push({
        bracket: `${formatCurrency(bracket.min)} - ${bracket.max === Infinity ? "+" : formatCurrency(bracket.max)} (${(bracket.rate * 100).toFixed(1)}%)`,
        amount,
      });
    }

    remaining -= taxableInBracket;
  }

  // Montreal extra bracket (2% over 500k, total 2.5%)
  const selectedMunicipality = SPECIAL_MUNICIPALITIES.find(
    (m) => m.name === municipality
  );
  if (selectedMunicipality?.hasExtraBracket && purchasePrice > MONTREAL_EXTRA_BRACKET.min) {
    const extraAmount = (purchasePrice - MONTREAL_EXTRA_BRACKET.min) * MONTREAL_EXTRA_BRACKET.rate;
    total += extraAmount;
    breakdown.push({
      bracket: `${formatCurrency(MONTREAL_EXTRA_BRACKET.min)}+ Montréal (0.5% add.)`,
      amount: extraAmount,
    });
  }

  return { total, breakdown };
}

// Estimate notary fees
function estimateNotaryFees(purchasePrice: number): {
  min: number;
  max: number;
  average: number;
} {
  // Typical Quebec notary fees (2024 estimates)
  if (purchasePrice <= 100000) {
    return { min: 800, max: 1200, average: 1000 };
  } else if (purchasePrice <= 250000) {
    return { min: 1000, max: 1500, average: 1250 };
  } else if (purchasePrice <= 500000) {
    return { min: 1200, max: 1800, average: 1500 };
  } else if (purchasePrice <= 1000000) {
    return { min: 1500, max: 2500, average: 2000 };
  } else {
    return { min: 2000, max: 3500, average: 2750 };
  }
}

// Format currency
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("fr-CA", {
    style: "currency",
    currency: "CAD",
    minimumFractionDigits: 2,
  }).format(amount);
}

// Calculate property tax adjustment
function calculateTaxAdjustment(
  annualTax: number,
  closingDate: Date,
  taxPaidBy: "seller" | "buyer"
): { sellerOwes: number; buyerOwes: number; explanation: string } {
  const year = closingDate.getFullYear();
  const startOfYear = new Date(year, 0, 1);
  const endOfYear = new Date(year, 11, 31);
  const totalDays = Math.ceil(
    (endOfYear.getTime() - startOfYear.getTime()) / (1000 * 60 * 60 * 24)
  ) + 1;

  const daysPassed = Math.ceil(
    (closingDate.getTime() - startOfYear.getTime()) / (1000 * 60 * 60 * 24)
  );
  const daysRemaining = totalDays - daysPassed;

  const sellerPortion = (daysPassed / totalDays) * annualTax;
  const buyerPortion = (daysRemaining / totalDays) * annualTax;

  if (taxPaidBy === "seller") {
    return {
      sellerOwes: 0,
      buyerOwes: buyerPortion,
      explanation: `Le vendeur a payé les taxes pour l'année. L'acheteur doit rembourser ${daysRemaining} jours (${formatCurrency(buyerPortion)}).`,
    };
  } else {
    return {
      sellerOwes: sellerPortion,
      buyerOwes: 0,
      explanation: `L'acheteur paiera les taxes. Le vendeur doit rembourser ${daysPassed} jours (${formatCurrency(sellerPortion)}).`,
    };
  }
}

export default function CalculatorPage() {
  // Transfer tax state
  const [purchasePrice, setPurchasePrice] = useState<string>("");
  const [municipality, setMunicipality] = useState<string>("Montréal");
  const [transferTaxResult, setTransferTaxResult] = useState<{
    total: number;
    breakdown: { bracket: string; amount: number }[];
    notaryFees: { min: number; max: number; average: number };
  } | null>(null);

  // Tax adjustment state
  const [annualTax, setAnnualTax] = useState<string>("");
  const [closingDate, setClosingDate] = useState<string>("");
  const [taxPaidBy, setTaxPaidBy] = useState<"seller" | "buyer">("seller");
  const [taxAdjustmentResult, setTaxAdjustmentResult] = useState<{
    sellerOwes: number;
    buyerOwes: number;
    explanation: string;
  } | null>(null);

  const calculateTransfer = () => {
    const price = parseFloat(purchasePrice.replace(/[^0-9.]/g, ""));
    if (isNaN(price) || price <= 0) return;

    const taxResult = calculateTransferTax(price, municipality);
    const notaryFees = estimateNotaryFees(price);
    setTransferTaxResult({ ...taxResult, notaryFees });
  };

  const calculateAdjustment = () => {
    const tax = parseFloat(annualTax.replace(/[^0-9.]/g, ""));
    if (isNaN(tax) || tax <= 0 || !closingDate) return;

    const result = calculateTaxAdjustment(tax, new Date(closingDate), taxPaidBy);
    setTaxAdjustmentResult(result);
  };

  const resetTransfer = () => {
    setPurchasePrice("");
    setMunicipality("Montréal");
    setTransferTaxResult(null);
  };

  const resetAdjustment = () => {
    setAnnualTax("");
    setClosingDate("");
    setTaxPaidBy("seller");
    setTaxAdjustmentResult(null);
  };

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <Calculator className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Calculateur</h1>
            <p className="text-muted-foreground">
              Outils de calcul pour les transactions immobilières au Québec
            </p>
          </div>
        </div>

        <Tabs defaultValue="transfer-tax" className="space-y-4">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="transfer-tax" className="gap-2">
              <Home className="h-4 w-4" />
              Droits de mutation
            </TabsTrigger>
            <TabsTrigger value="tax-adjustment" className="gap-2">
              <Calendar className="h-4 w-4" />
              Ajustement taxes
            </TabsTrigger>
          </TabsList>

          {/* Transfer Tax Calculator */}
          <TabsContent value="transfer-tax" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <DollarSign className="h-5 w-5" />
                  Droits de mutation (Taxe de bienvenue)
                </CardTitle>
                <CardDescription>
                  Calculez les droits de mutation immobilière selon les taux du Québec
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="purchase-price">Prix d'achat ($)</Label>
                    <Input
                      id="purchase-price"
                      type="text"
                      placeholder="450 000"
                      value={purchasePrice}
                      onChange={(e) => setPurchasePrice(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && calculateTransfer()}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="municipality">Municipalité</Label>
                    <Select value={municipality} onValueChange={setMunicipality}>
                      <SelectTrigger id="municipality">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {SPECIAL_MUNICIPALITIES.map((m) => (
                          <SelectItem key={m.name} value={m.name}>
                            {m.name}
                            {m.hasExtraBracket && (
                              <span className="text-muted-foreground ml-2">
                                (taux majoré)
                              </span>
                            )}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button onClick={calculateTransfer} className="flex-1">
                    <Calculator className="h-4 w-4 mr-2" />
                    Calculer
                  </Button>
                  <Button variant="outline" onClick={resetTransfer}>
                    <RotateCcw className="h-4 w-4" />
                  </Button>
                </div>

                {/* Info box */}
                <div className="p-3 bg-muted/50 rounded-lg flex gap-2 text-sm">
                  <Info className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                  <div className="text-muted-foreground">
                    <strong>Taux 2024:</strong> 0.5% (0-58 900$), 1.0% (58 900-294 600$),
                    1.5% (294 600$+). Montréal: +0.5% au-delà de 500 000$.
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Results */}
            {transferTaxResult && (
              <Card className="border-primary/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg">Résultat du calcul</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Main result */}
                  <div className="p-4 bg-primary/10 rounded-lg text-center">
                    <p className="text-sm text-muted-foreground mb-1">
                      Droits de mutation à payer
                    </p>
                    <p className="text-3xl font-bold text-primary">
                      {formatCurrency(transferTaxResult.total)}
                    </p>
                  </div>

                  {/* Breakdown */}
                  <div className="space-y-2">
                    <p className="text-sm font-medium">Détail par tranche:</p>
                    <div className="space-y-1">
                      {transferTaxResult.breakdown.map((item, i) => (
                        <div
                          key={i}
                          className="flex justify-between text-sm py-1 border-b border-dashed last:border-0"
                        >
                          <span className="text-muted-foreground">{item.bracket}</span>
                          <span className="font-medium">{formatCurrency(item.amount)}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Notary fees estimate */}
                  <div className="p-3 bg-muted/50 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <FileText className="h-4 w-4" />
                      <p className="text-sm font-medium">Honoraires de notaire estimés</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">
                        {formatCurrency(transferTaxResult.notaryFees.min)} -
                        {formatCurrency(transferTaxResult.notaryFees.max)}
                      </span>
                      <Badge variant="secondary">
                        ~{formatCurrency(transferTaxResult.notaryFees.average)}
                      </Badge>
                    </div>
                  </div>

                  {/* Total estimated */}
                  <div className="pt-2 border-t">
                    <div className="flex justify-between items-center">
                      <span className="font-medium">Total estimé (avec notaire)</span>
                      <span className="text-lg font-bold">
                        {formatCurrency(
                          transferTaxResult.total + transferTaxResult.notaryFees.average
                        )}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      *Les honoraires de notaire sont une estimation et peuvent varier
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Tax Adjustment Calculator */}
          <TabsContent value="tax-adjustment" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5" />
                  Ajustement des taxes foncières
                </CardTitle>
                <CardDescription>
                  Calculez le remboursement de taxes entre vendeur et acheteur
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="annual-tax">Taxes foncières annuelles ($)</Label>
                    <Input
                      id="annual-tax"
                      type="text"
                      placeholder="4 500"
                      value={annualTax}
                      onChange={(e) => setAnnualTax(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="closing-date">Date de clôture</Label>
                    <Input
                      id="closing-date"
                      type="date"
                      value={closingDate}
                      onChange={(e) => setClosingDate(e.target.value)}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Taxes payées par</Label>
                  <Select
                    value={taxPaidBy}
                    onValueChange={(v) => setTaxPaidBy(v as "seller" | "buyer")}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="seller">
                        Vendeur (déjà payées pour l'année)
                      </SelectItem>
                      <SelectItem value="buyer">
                        Acheteur (paiera à la clôture)
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex gap-2">
                  <Button onClick={calculateAdjustment} className="flex-1">
                    <Calculator className="h-4 w-4 mr-2" />
                    Calculer l'ajustement
                  </Button>
                  <Button variant="outline" onClick={resetAdjustment}>
                    <RotateCcw className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Results */}
            {taxAdjustmentResult && (
              <Card className="border-primary/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg">Ajustement calculé</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="p-4 bg-muted/50 rounded-lg text-center">
                      <p className="text-sm text-muted-foreground mb-1">
                        Vendeur doit
                      </p>
                      <p className="text-2xl font-bold">
                        {formatCurrency(taxAdjustmentResult.sellerOwes)}
                      </p>
                    </div>
                    <div className="p-4 bg-primary/10 rounded-lg text-center">
                      <p className="text-sm text-muted-foreground mb-1">
                        Acheteur doit
                      </p>
                      <p className="text-2xl font-bold text-primary">
                        {formatCurrency(taxAdjustmentResult.buyerOwes)}
                      </p>
                    </div>
                  </div>

                  <div className="p-3 bg-muted/50 rounded-lg">
                    <p className="text-sm">{taxAdjustmentResult.explanation}</p>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </AppShell>
  );
}
