// Starter list of Indian Oil retail products, so a station can add them in one tap.
// Prices and availability differ by outlet: add what you actually sell, and add anything missing as a custom product.
export const INDIANOIL_CATALOGUE = [
  { group: "Petrol", items: [
    { name: "Petrol (MS)", category: "Fuel", unit: "L" },
    { name: "XP95 Petrol", category: "Fuel", unit: "L" },
    { name: "XP100 Petrol", category: "Fuel", unit: "L" },
  ] },
  { group: "Diesel", items: [
    { name: "Diesel (HSD)", category: "Fuel", unit: "L" },
    { name: "XtraGreen Diesel", category: "Fuel", unit: "L" },
  ] },
  { group: "Gas", items: [
    { name: "CNG", category: "Gas", unit: "Kg" },
    { name: "Auto LPG", category: "Gas", unit: "L" },
  ] },
  { group: "SERVO engine oils", items: [
    { name: "Servo Hyper Sport (motorcycle)", category: "Lubricant", unit: "L" },
    { name: "Servo Hyper Drive (car / SUV)", category: "Lubricant", unit: "L" },
    { name: "Servo Hyper Drive NXT", category: "Lubricant", unit: "L" },
    { name: "Servo Hyper Torq (commercial)", category: "Lubricant", unit: "L" },
    { name: "Servo SuperMile Plus", category: "Lubricant", unit: "L" },
    { name: "Servo SuperMile (diesel)", category: "Lubricant", unit: "L" },
    { name: "Servo Honda Josh 10W30 MA", category: "Lubricant", unit: "L" },
    { name: "Servo Honda ScootoNXT 10W30 MB", category: "Lubricant", unit: "L" },
  ] },
  { group: "Other SERVO products", items: [
    { name: "Servo Gear Oil", category: "Lubricant", unit: "L" },
    { name: "Servo Coolant", category: "Lubricant", unit: "L" },
    { name: "Servo Brake Fluid", category: "Lubricant", unit: "L" },
    { name: "Servo Grease", category: "Lubricant", unit: "Kg" },
  ] },
];
