import QuantLib as ql
from scipy.optimize import linprog
import csv
from datetime import datetime

## INPUTS

inputBonds = "/Users/adamfee/Desktop/Math4820/ProjectOne/TreasuryPrices9Sep24.csv"
inputCashFlows = "/Users/adamfee/Desktop/Math4820/ProjectOne/SingleCFShort.csv"
outputPath = "/Users/adamfee/Desktop/Math4820/ProjectOne/test.csv"
settlementDate = ql.Date(25, 9, 2024)



## HELPER CASH FLOW

def bondCashFlows(settlementDate, maturityDate):
    start = maturityDate
    while start > settlementDate:
        start = start - ql.Period(6, ql.Months)

    calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)
    
    if calendar.isEndOfMonth(maturityDate):
        start = ql.Calendar.endOfMonth(calendar, start)

    schedule = ql.Schedule(
        start, maturityDate, ql.Period(ql.Semiannual),
        calendar,
        ql.Unadjusted, ql.Unadjusted,
        ql.DateGeneration.Backward, 
        calendar.isEndOfMonth(maturityDate)
    )

    return schedule



## INPUT REQUIRED CASH FLOWS

cashFlows = []
with open(inputCashFlows, newline="") as file:
    next(csv.reader(file))
    for row in csv.reader(file):
        if not row:
            continue

        date, cashFlow = row

        d = datetime.strptime(date.strip(), "%B %d, %Y").date()
        cashFlows.append({
            "date": ql.Date(d.day, d.month, d.year),
            "cashFlow": float(cashFlow.strip())
        })

    cashFlows.sort(key=lambda cf: cf["date"])
    finalCashFlowDate = cashFlows[-1]["date"]



## INPUT BOND WRITER

bonds = []
with open(inputBonds, newline="") as file:
    for row in csv.reader(file):
        cusip, secType, rate, maturityDate, extra, callDate, buy, sell = row
        if secType.strip() not in ("MARKET BASED BILL",
                                   "MARKET BASED NOTE",
                                   "MARKET BASED BOND"):
            continue
        
        d = datetime.strptime(row[3].strip(), "%m/%d/%Y").date()
        maturityDate = ql.Date(d.day, d.month, d.year)
        if maturityDate <= settlementDate or maturityDate > finalCashFlowDate:
            continue

        bond = ql.FixedRateBond(1, 100, bondCashFlows(settlementDate, maturityDate), [float(rate)], ql.ActualActual(ql.ActualActual.ISMA), ql.Unadjusted)

        flows = []
        for f in bond.cashflows():
            if f.date() > settlementDate:
                flows.append((f.date(), f.amount()))

        bonds.append({
            "cusip": row[0].strip(),
            "secType": row[1].strip(),
            "rate": float(row[2].strip()),
            "maturityDate": maturityDate,
            "buy": float(row[5].strip()),
            "dirtyPrice": float(row[5].strip()) + float(bond.accruedAmount(settlementDate)),
            "flows": flows
        })


## MATRICES

b = []
total = 0.0
for cf in cashFlows:
    total += cf["cashFlow"]
    b.append(-total)

A = []
for cf in cashFlows:
    row = []
    for bond in bonds:
        received = sum(amt for (d, amt) in bond["flows"] if d <= cf["date"])
        row.append(-received / 100)
    A.append(row)

c = []
for bond in bonds:
    c.append(bond["dirtyPrice"]/100)

result = linprog(c, A_ub=A, b_ub=b, method="highs")



## OUTPUT WRITER

with open(outputPath, "w", newline="") as out:
    writer = csv.writer(out)
    writer.writerow(["CUSIP", "Principal"])
    for bond, amount in zip(bonds, result.x):
        if (amount > 1e-6):
            writer.writerow([bond["cusip"], round(amount, 2)])