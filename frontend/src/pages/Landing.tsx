import { Link } from 'react-router-dom'
import {
  ArrowRight,
  Bot,
  Camera,
  CheckCircle2,
  Droplets,
  FlaskConical,
  Gauge,
  Leaf,
  LineChart,
  Mountain,
  ShieldCheck,
  Sprout,
  Timer,
  Upload,
} from 'lucide-react'
import { Alert, Card } from '../components/ui'

const FEATURES = [
  {
    icon: Droplets,
    title: 'Smart Irrigation Prediction',
    body: 'Enter soil moisture, temperature, humidity, rainfall and growth stage. Get a clear answer: irrigate or not, how much water, for how long, and why.',
    points: ['Water requirement in mm and litres', 'Duration and best time of day', 'Low / Medium / High / Critical priority'],
    tone: 'text-sky-600 bg-sky-50 dark:bg-sky-950 dark:text-sky-300',
  },
  {
    icon: Leaf,
    title: 'Sugarcane Disease Detection',
    body: 'Upload a photo of a leaf or stalk. The system reports the likely condition, its confidence, and how severe the visible symptoms are.',
    points: ['Red rot, rust, smut, mosaic, leaf scald, yellow leaf', 'Confidence score and severity rating', 'Says "unknown" rather than guessing'],
    tone: 'text-cane-600 bg-cane-50 dark:bg-cane-950 dark:text-cane-300',
  },
  {
    icon: Mountain,
    title: 'Soil Photo Analysis',
    body: 'Photograph bare soil for a visual estimate of soil category, moisture appearance and texture - with the limits of photo analysis stated plainly.',
    points: ['Black, red, sandy, clay or loamy', 'Moisture and organic matter appearance', 'Never claims NPK or pH from a photo'],
    tone: 'text-soil-600 bg-soil-50 dark:bg-soil-950 dark:text-soil-300',
  },
  {
    icon: Sprout,
    title: 'Variety Recommendation',
    body: 'Rank sugarcane varieties against your soil, region, climate and water availability, from an editable knowledge base you can correct for your district.',
    points: ['Match score with the reasoning shown', 'Water requirement and maturity', 'Cautions, not just selling points'],
    tone: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-950 dark:text-emerald-300',
  },
  {
    icon: FlaskConical,
    title: 'Fertilizer Guidance',
    body: 'Stage-based nutrient priorities and split timing, adjusted for your soil type and any laboratory values you have.',
    points: ['N, P, K priority per growth stage', 'Split application schedule', 'No unsafe fixed dosages'],
    tone: 'text-violet-600 bg-violet-50 dark:bg-violet-950 dark:text-violet-300',
  },
  {
    icon: Bot,
    title: 'Sugarcane Assistant',
    body: 'Ask questions in plain language. Answers draw on your own saved analyses and cite which records they used.',
    points: ['Explains your results simply', 'Tells you when it is unsure', 'Kannada and Hindi planned'],
    tone: 'text-amber-600 bg-amber-50 dark:bg-amber-950 dark:text-amber-300',
  },
]

const STEPS = [
  {
    icon: Upload,
    title: 'Enter conditions or upload a photo',
    body: 'Type in soil moisture and weather, or take a photo of a leaf or a patch of bare soil. Nothing special is needed - a phone camera in daylight is enough.',
  },
  {
    icon: Gauge,
    title: 'The system analyses it',
    body: 'A water-balance model plus a trained machine-learning model handle irrigation. Image analysis handles crop and soil photos. Every result says which produced it.',
  },
  {
    icon: LineChart,
    title: 'Act on a clear recommendation',
    body: 'You get the decision, the numbers behind it, and the reasoning in plain language - plus a recovery plan when something is wrong.',
  },
  {
    icon: Timer,
    title: 'Track it over time',
    body: 'Every analysis is saved. Upload follow-up photos to see whether the crop is improving or getting worse, and watch your irrigation pattern build up.',
  },
]

const BENEFITS = [
  { title: 'Cut water waste', body: 'Irrigate on measured need rather than a fixed calendar. The system defers irrigation when rain is forecast instead of watering anyway.' },
  { title: 'Catch problems earlier', body: 'A weekly photo takes seconds. Spotting red rot at a few clumps rather than across the block is the difference between roguing and replanting.' },
  { title: 'Lower pumping cost', body: 'Less water applied means fewer pump hours and lower electricity or diesel spend, with the same crop water use.' },
  { title: 'Understand your soil', body: 'A visual estimate plus honest limitations, so you know exactly when a laboratory test is the thing you actually need.' },
  { title: 'Keep a farm record', body: 'Every irrigation decision, plant photo and soil check stored with its date, ready to show an agricultural officer.' },
  { title: 'Works without sensors', body: 'No soil moisture sensor? The built-in simulator estimates it from a water balance so you can still plan.' },
]

export default function Landing() {
  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-b from-cane-50 via-white to-white dark:from-cane-950/40 dark:via-slate-950 dark:to-slate-950">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.35] dark:opacity-20"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 15%, rgba(34,197,94,0.22), transparent 45%), radial-gradient(circle at 85% 25%, rgba(14,165,233,0.16), transparent 42%)',
          }}
        />
        <div className="section relative py-20 lg:py-28">
          <div className="mx-auto max-w-3xl text-center">
            <span className="inline-flex items-center gap-2 rounded-full border border-cane-200 bg-white px-4 py-1.5 text-xs font-semibold text-cane-800 shadow-sm dark:border-cane-800 dark:bg-slate-900 dark:text-cane-300">
              <Leaf className="size-3.5" />
              AI-driven precision irrigation scheduling for sugarcane
            </span>

            <h1 className="mt-6 font-display text-4xl font-extrabold leading-[1.1] tracking-tight sm:text-5xl lg:text-6xl">
              AI-Powered <span className="text-cane-600">Smart Sugarcane</span> Farming
            </h1>

            <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-slate-600 dark:text-slate-400">
              Analyze crop health, detect possible diseases, understand your soil, receive irrigation
              recommendations, and get intelligent crop management guidance.
            </p>

            <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Link to="/plant-analysis" className="btn-primary w-full sm:w-auto">
                <Camera className="size-4" />
                Analyze My Plant
              </Link>
              <Link to="/irrigation" className="btn-secondary w-full sm:w-auto">
                <Droplets className="size-4" />
                Check Irrigation
              </Link>
              <Link to="/soil-analysis" className="btn-secondary w-full sm:w-auto">
                <Mountain className="size-4" />
                Analyze Soil
              </Link>
            </div>

            <p className="mt-5 text-xs text-slate-500 dark:text-slate-400">
              Free to run locally. Create an account to save your analyses.
            </p>
          </div>

          <div className="mx-auto mt-16 grid max-w-4xl grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { value: '9', label: 'Environmental inputs' },
              { value: '7', label: 'Crop conditions' },
              { value: '5', label: 'Soil categories' },
              { value: '12', label: 'Sugarcane varieties' },
            ].map((stat) => (
              <Card key={stat.label} className="p-4 text-center">
                <p className="font-display text-3xl font-extrabold text-cane-600">{stat.value}</p>
                <p className="mt-1 text-xs font-medium text-slate-500 dark:text-slate-400">{stat.label}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Honesty notice */}
      <section className="section py-4">
        <Alert tone="info" title="How this system talks about its own accuracy" icon={ShieldCheck}>
          Every AI result in this application states how it was produced: a{' '}
          <strong>trained model</strong>, a documented <strong>rule engine</strong>, or a clearly
          labelled <strong>demo heuristic</strong>. Image analysis runs in demo mode until you train a
          model on a real labelled dataset, and the interface says so on every result rather than
          presenting an estimate as a diagnosis.
        </Alert>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="section scroll-mt-20 py-16 lg:py-20">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="font-display text-3xl font-extrabold sm:text-4xl">How It Works</h2>
          <p className="mt-4 text-slate-600 dark:text-slate-400">
            Four steps, from a phone photo or a moisture reading to a decision you can act on today.
          </p>
        </div>

        <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, index) => {
            const Icon = step.icon
            return (
              <Card key={step.title} hover className="relative p-6">
                <span className="absolute right-5 top-5 font-display text-4xl font-extrabold text-slate-100 dark:text-slate-800">
                  {index + 1}
                </span>
                <span className="grid size-12 place-items-center rounded-2xl bg-cane-600 text-white shadow-sm">
                  <Icon className="size-6" />
                </span>
                <h3 className="mt-4 text-base font-bold">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                  {step.body}
                </p>
              </Card>
            )
          })}
        </div>
      </section>

      {/* Features */}
      <section
        id="features"
        className="scroll-mt-20 border-y border-slate-200 bg-slate-50 py-16 lg:py-20 dark:border-slate-800 dark:bg-slate-900/40"
      >
        <div className="section">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="font-display text-3xl font-extrabold sm:text-4xl">AI Features</h2>
            <p className="mt-4 text-slate-600 dark:text-slate-400">
              Six modules, each producing a specific decision rather than a general score.
            </p>
          </div>

          <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature) => {
              const Icon = feature.icon
              return (
                <Card key={feature.title} hover className="flex flex-col p-6">
                  <span className={`grid size-12 place-items-center rounded-2xl ${feature.tone}`}>
                    <Icon className="size-6" />
                  </span>
                  <h3 className="mt-4 text-base font-bold">{feature.title}</h3>
                  <p className="mt-2 flex-1 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                    {feature.body}
                  </p>
                  <ul className="mt-4 space-y-2 border-t border-slate-100 pt-4 dark:border-slate-800">
                    {feature.points.map((point) => (
                      <li
                        key={point}
                        className="flex items-start gap-2 text-xs text-slate-600 dark:text-slate-400"
                      >
                        <CheckCircle2 className="mt-0.5 size-3.5 shrink-0 text-cane-600" />
                        {point}
                      </li>
                    ))}
                  </ul>
                </Card>
              )
            })}
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section id="benefits" className="section scroll-mt-20 py-16 lg:py-20">
        <div className="grid gap-12 lg:grid-cols-[1fr_1.3fr] lg:items-start">
          <div className="lg:sticky lg:top-24">
            <h2 className="font-display text-3xl font-extrabold sm:text-4xl">Benefits</h2>
            <p className="mt-4 leading-relaxed text-slate-600 dark:text-slate-400">
              Sugarcane is water-intensive and grown over a long season, so small improvements in
              timing compound. The point of this system is not to replace your judgement - it is to
              put the numbers in front of you before you start the pump.
            </p>
            <Link to="/register" className="btn-primary mt-6">
              Create a free account
              <ArrowRight className="size-4" />
            </Link>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {BENEFITS.map((benefit) => (
              <Card key={benefit.title} className="p-5">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-cane-600" />
                  <div>
                    <h3 className="text-sm font-bold">{benefit.title}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                      {benefit.body}
                    </p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="section pb-20">
        <div className="overflow-hidden rounded-3xl bg-gradient-to-br from-cane-700 to-cane-900 px-8 py-14 text-center shadow-xl">
          <h2 className="font-display text-3xl font-extrabold text-white sm:text-4xl">
            Start with one field
          </h2>
          <p className="mx-auto mt-4 max-w-xl leading-relaxed text-cane-100">
            Run one irrigation check and upload one plant photo. That is enough to see whether the
            recommendations match what you already know about your crop.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              to="/register"
              className="btn w-full bg-white text-cane-800 hover:bg-cane-50 sm:w-auto"
            >
              Get started free
              <ArrowRight className="size-4" />
            </Link>
            <Link
              to="/login"
              className="btn w-full border border-cane-400/60 text-white hover:bg-cane-800 sm:w-auto"
            >
              I already have an account
            </Link>
          </div>
        </div>
      </section>
    </>
  )
}
